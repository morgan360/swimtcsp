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
from .models import PaymentNotification
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
base_order_id = "TCSP005"
timestamp = time.strftime("%Y%m%d%H%M%S")
order_id = f"{base_order_id}_{timestamp}"


def initiate_boipa_payment_session(request, total_price, order_ref):
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


# def get_boipa_session_token():
#     url = BOIPA_TOKEN_URL  # UAT URL, change for production
#     headers = {'Content-Type': 'application/x-www-form-urlencoded'}
#     payload = {
#         "merchantId": settings.BOIPA_MERCHANT_ID,
#         "password": settings.BOIPA_PASSWORD,
#         "action": "AUTH",  # Based on the operation you're performing
#         "timestamp": int(time.time() * 1000),  # Current time in milliseconds
#         "allowOriginUrl": NGROK,  # Your ngrok URL for CORS
#         "channel": "ECOM",
#         "country": "IE",  # Example country code
#         "currency": "EUR",  # Example currency
#         "amount": "100.00",  # Example amount for AUTH or PURCHASE
#         "merchantTxId": order_id,  # Your internal order ID
#         "merchantLandingPageUrl": NGROK + "/boipa/payment-response/",  # General callback URL for customer redirection
#         "merchantNotificationUrl": NGROK + "/boipa/payment-notification/",  # Server-to-server notification URL(
#         # important
#         # in case user makes a mess)
#         "merchantLandingPageRedirectMethod": "GET",  # Ensure redirects use GET
#     }

    # response = requests.post(url, data=payload, headers=headers)
    # if response.status_code == 200:
    #     return response.json().get('token')
    # else:
    #     # Handle error
    #     print(f"Error obtaining session token: {response.text}")
    #     return None


# def load_payment_form(request):
#     token = get_boipa_session_token()
#     if token is None:
#         return render(request, 'error.html', {'error': 'Unable to obtain session token.'})
#
#     # Construct the HPP URL with the obtained token and include integrationMode
#     hpp_url = HPP_FORM + f"?token={token}&merchantId={settings.BOIPA_MERCHANT_ID}&integrationMode=Standalone"
#
#     # Redirect user to the HPP URL
#     return redirect(hpp_url)


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
        # Parse the URL-encoded form data
        data = QueryDict(request.body)

        # Now, you can access the values using the same dictionary-like interface
        txId = data.get('txId')# The unique identifier for the transaction in the BOIPA Gateway
        merchantTxId = data.get('merchantTxId')# The merchant’s reference for the transaction provided in the
        country = data.get('country')
        amount = data.get('amount')
        currency = data.get('currency')
        action = data.get('action')
        auth_code = data.get('auth_code') # Extracted from paymentSolutionDetails
        acquirer = data.get('acquirer')
        acquirerAmount = data.get('acquirerAmount')
        merchantId = data.get('merchantId')
        brandId = data.get('brandId')
        customerId = data.get('customerId')
        acquirerCurrency = data.get(' acquirerCurrency')
        paymentSolutionId = data.get('paymentSolutionId')
        status = data.get('status')

        # Proceed with your logic

        # You can adjust the fields based on what's most relevant to your needs
        # Store the collected data in the database
        PaymentNotification.objects.create(
            txId=txId,
            merchantTxId = merchantTxId,
            country = country,
            amount = amount,
            currency = currency,
            action = action,
            auth_code = auth_code,
            acquirer = acquirer,
            acquirerAmount = acquirerAmount,
            merchantId =merchantId,
            brandId = brandId,
            customerId = customerId,
            acquirerCurrency = acquirerCurrency,
            paymentSolutionId = paymentSolutionId,
            status = status,
        )
