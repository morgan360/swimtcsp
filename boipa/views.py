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
from .models import SwimOrderPaymentNotification, LessonOrderPaymentNotification, SchoolOrderPaymentNotification
from swims_orders.models import Order as SwimOrder
from lessons_orders.models import Order as LessonOrder
from schools_orders.models import Order as SchoolOrder
from django.http import QueryDict
from django.urls import reverse
from lessons_bookings.utils.enrollment import handle_lessons_enrollment

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
    print(total_price)
    print(order_ref)
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
        "merchantTxId": order_ref,  # Example: product ID as transaction ID
        "merchantLandingPageUrl": NGROK + reverse('boipa:payment_response'),
        "merchantNotificationUrl": NGROK + reverse('boipa:payment_notification'),
        "merchantLandingPageRedirectMethod": "GET",
    }
    print('PAYLOAD', payload)
    # Send the request to BOIPA to initiate the payment session
    response = requests.post(BOIPA_TOKEN_URL, data=payload,
                             headers={'Content-Type': 'application/x-www-form-urlencoded'})
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


# Also in views.py

def payment_response(request):
    """
    Handles the payment response from BOIPA.
    """
    result = request.GET.get('result')
    merchantTxId = request.GET.get('merchantTxId')
    source_prefix, order_id_str = merchantTxId.split("_", 1)
    order_ref = merchantTxId
    order_id = int(order_id_str)

    if result == "success":
        if source_prefix == "swim":
            order = SwimOrder.objects.get(id=order_id)
        elif source_prefix == "lessons":
            order = LessonOrder.objects.get(id=order_id)
        elif source_prefix == "schools":
            order = SchoolOrder.objects.get(id=order_id)

        order.paid = True
        order.save()

        # Payment was successful
        return render(request, 'payment_success.html', {'order_ref ': merchantTxId})
    elif result == "failure":
        # Payment failed
        return render(request, 'payment_failure.html', {'order_ref ': merchantTxId})
    else:
        # Unrecognized result
        return render(request, 'error.html', {'error_message': 'Unknown payment response.'})

###### Notifications #######
@csrf_exempt  # Disable CSRF protection for this endpoint
def payment_notification(request):
    if request.method == 'POST':
        data = QueryDict(request.body)
        # Extracting the necessary information
        merchantTxId = data.get('merchantTxId')
        source_prefix, order_id_str = merchantTxId.split("_", 1)
        order_id = int(order_id_str)
        if source_prefix == 'swims':
            # Parse the URL-encoded form data
            data = QueryDict(request.body)
            order_obj = SwimOrder.objects.get(id=order_id)

            # Create a payment notification record
            SwimOrderPaymentNotification.objects.create(
                order=order_obj,
                txId=data.get('txId'),
                merchantTxId=data.get('merchantTxId'),
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
                status=data.get('status'),
            )

            # Return a successful HTTP response
            return HttpResponse('Payment processed successfully', status=200)

        elif source_prefix == 'lessons':
            # Parse the URL-encoded form data
            data = QueryDict(request.body)
            order_obj = LessonOrder.objects.get(id=order_id)
            # Create a payment notification record
            LessonOrderPaymentNotification.objects.create(
                order=order_obj,
                txId=data.get('txId'),
                merchantTxId=data.get('merchantTxId'),
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
                status=data.get('status'),
                 )
            return HttpResponse('Payment processed successfully', status=200)

        elif source_prefix == 'schools':
            data = QueryDict(request.body)
            order_obj =SchoolOrder.objects.get(id=order_id)
            # Create a payment notification record
            SchoolOrderPaymentNotification.objects.create(
                order=order_obj,
                txId=data.get('txId'),
                merchantTxId=data.get('merchantTxId'),
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

    else:
        # If not a POST request, indicate it's an invalid request method
        return HttpResponse("Invalid request method", status=405)
