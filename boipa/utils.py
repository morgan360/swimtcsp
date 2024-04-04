# boipa/utils.py

import requests
from django.conf import settings
from urllib.parse import urlencode

def initiate_boipa_payment(order_id, amount):
    success_url = settings.YOUR_SUCCESS_URL  # Define how you construct success URL
    cancel_url = settings.YOUR_CANCEL_URL    # Define how you construct cancel URL
    payload = {
        "merchantId": settings.BOIPA_MERCHANT_ID,
        "password": settings.BOIPA_PASSWORD,
        "action": "PURCHASE",
        # Include other necessary parameters as per your existing setup
        "amount": amount,
        "order_id": order_id,
        "successUrl": success_url,
        "cancelUrl": cancel_url,
    }
    # Make the request to BOIPA to get a session token
    response = requests.post(settings.BOIPA_TOKEN_URL, data=payload)
    if response.status_code == 200:
        # Assuming the response contains a token and/or a URL to redirect to
        token = response.json().get('token')
        payment_url = f"{settings.BOIPA_PAYMENT_FORM_URL}?token={token}"
        return payment_url
    else:
        return None
