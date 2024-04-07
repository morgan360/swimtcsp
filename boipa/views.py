from django.shortcuts import render, redirect
import requests
import os
import logging
from urllib.parse import urlencode
from dotenv import load_dotenv
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.conf import settings
import time
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import SwimOrderPaymentNotification, LessonOrderPaymentNotification
from swims_orders.models import Order as SwimOrder
from lessons_orders.models import Order as LessonOrder
from django.http import QueryDict
from django.urls import reverse
# Load environment variables
load_dotenv()

# Initialize logging
logger = logging.getLogger(__name__)

# Environment variables
BOIPA_MERCHANT_ID = os.getenv('BOIPA_MERCHANT_ID')
BOIPA_PASSWORD = os.getenv('BOIPA_PASSWORD')
BOIPA_TOKEN_URL = os.getenv('BOIPA_TOKEN_URL')  # URL to obtain the session token
PAYMENT_FORM_URL = os.getenv('HPP_FORM')  # URL for the payment form
NGROK = os.getenv('NGROK')  # For ip tunnel from BOIPA
HPP_FORM = os.getenv('HPP_FORM')
timestamp = time.strftime("%Y%m%d%H%M%S")



def initiate_boipa_payment_session(request, order_ref, total_price):
    """
    Initiates a payment session with BOIPA for a given product and total price.
    Redirects the user to the BOIPA payment page.
    """
    # Construct the payload with your details
    payload = {
        "merchantId": BOIPA_MERCHANT_ID,
        "password": BOIPA_PASSWORD,
        "action": "AUTH",  # Change as needed
        "timestamp": str(int(time.time() * 1000)),
        "allowOriginUrl": NGROK,  # The URL BOIPA should allow origin from
        "channel": "ECOM",
        "country": "IE",  # Example: IE for Ireland
        "currency": "EUR",
        "amount": str(total_price),
        "merchantTxId": str(order_ref),  # Example: product ID as transaction ID
        "merchantLandingPageUrl": NGROK + reverse('boipa:payment_response'),
        "merchantNotificationUrl": NGROK + reverse('boipa:payment_notification'),
        "merchantLandingPageRedirectMethod": "GET",
    }

    # Send the request to BOIPA to initiate the payment session
    response = requests.post(BOIPA_TOKEN_URL, data=payload, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    if response.status_code == 200:
        # Extract the session token from the response
        session_token = response.json().get('token')
        # Construct the payment URL
        payment_url = f"{PAYMENT_FORM_URL}?token={session_token}&merchantId={BOIPA_MERCHANT_ID}&integrationMode=Standalone"
        # Redirect the user to the BOIPA payment page
        return redirect(payment_url)
    else:
        # Handle error (e.g., display an error message)
        return render(request, 'error.html', {'error_message': 'Failed to initiate payment session.'})


def error_view(request):
    # Example error handling logic
    error_message = "An unexpected error has occurred."
    return render(request, 'error.html', {'error_message': error_message})


# Also in views.py

def payment_response(request):
    """
    Handles the payment response from BOIPA.
    """
    result = request.GET.get('result')
    merchant_tx_id = request.GET.get('merchantTxId')

    if result == "success":
        # Payment was successful
        return render(request, 'payment_success.html', {'merchant_tx_id': merchant_tx_id})
    elif result == "failure":
        # Payment failed
        return render(request, 'payment_failure.html', {'merchant_tx_id': merchant_tx_id})
    else:
        # Unrecognized result
        return render(request, 'error.html', {'error_message': 'Unknown payment response.'})


@csrf_exempt  # Disable CSRF protection for this endpoint
def payment_notification(request):
    if request.method == 'POST':
        data = QueryDict(request.body)
# Extracting the necessary information
        txId = data.get('txId')
        merchantTxId = data.get('merchantTxId')
        status = data.get('status')
        try:
            source_prefix, order_id_str = merchantTxId.split("_", 1)
            order_id = int(order_id_str)
        except ValueError:
            # If conversion fails, respond with an error indicating bad data
            return HttpResponse("Invalid order ID format", status=400)

        if source_prefix == 'swims':
            try:
                order = SwimOrder.objects.get(id=order_id)  # Assuming merchantTxId is the Order ID
                order.txId = txId
                order.payment_status = status
                if status == 'SET_FOR_CAPTURE' or status == 'CAPTURED':
                    order.paid = True
                else:
                    order.paid = False
                order.save()

                # Create a payment notification record
                SwimOrderPaymentNotification.objects.create(
                    order=order,
                    txId=txId,
                    merchantTxId=merchantTxId,
                    country=data.get('country'),
                    amount=data.get('amount'),
                    currency=data.get('currency'),
                    action=data.get('action'),
                    # Assuming auth_code and other details are extracted correctly from paymentSolutionDetails or similar
                    # auth_code=data.get('auth_code'),
                    acquirer=data.get('acquirer'),
                    acquirerAmount=data.get('acquirerAmount'),
                    merchantId=data.get('merchantId'),
                    brandId=data.get('brandId'),
                    customerId=data.get('customerId'),
                    acquirerCurrency=data.get('acquirerCurrency'),
                    paymentSolutionId=data.get('paymentSolutionId'),
                    status=data.get('status'), )

                return HttpResponse("Notification processed successfully", status=200)
            except Order.DoesNotExist:
                # Handle case where the order does not exist
                return HttpResponse("Order not found", status=400)

        elif source_prefix == 'lessons':
            try:
                order = LessonOrder.objects.get(id=order_id)  # Assuming merchantTxId is the Order ID
                # order.txId = txId
                # order.payment_status = status
                # if status == 'SET_FOR_CAPTURE' or status == 'CAPTURED':
                #     order.paid = True
                # else:
                #     order.paid = False
                # order.save()

                # Create a payment notification record
                LessonOrderPaymentNotification.objects.create(
                    order=order,
                    txId=txId,
                    merchantTxId=merchantTxId,
                    country=data.get('country'),
                    amount=data.get('amount'),
                    currency=data.get('currency'),
                    action=data.get('action'),
                    # Assuming auth_code and other details are extracted correctly from paymentSolutionDetails or similar
                    # auth_code=data.get('auth_code'),
                    acquirer=data.get('acquirer'),
                    acquirerAmount=data.get('acquirerAmount'),
                    merchantId=data.get('merchantId'),
                    brandId=data.get('brandId'),
                    customerId=data.get('customerId'),
                    acquirerCurrency=data.get('acquirerCurrency'),
                    paymentSolutionId=data.get('paymentSolutionId'),
                    status=data.get('status'), )

                return HttpResponse("Notification processed successfully", status=200)
            except Order.DoesNotExist:
                # Handle case where the order does not exist
                return HttpResponse("Order not found", status=400)

        else:
            # If not a POST request, indicate it's an invalid request method
            return HttpResponse("Invalid request method", status=405)
