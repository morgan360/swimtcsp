# boipa/utils.py
import requests
from django.conf import settings
from urllib.parse import urlencode
from decimal import Decimal
import logging


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

####  REFUNDS ####

logger = logging.getLogger("boipa")

def refund_boipa_transaction(tx_id, amount, currency="EUR", order=None):
    """
    Send a refund request to the BOIPA Gateway and optionally log or store the refund.
    """
    payload = {
        "merchantId": settings.BOIPA_MERCHANT_ID,
        "password": settings.BOIPA_PASSWORD,
        "action": "REFUND",
        "txId": tx_id,
        "amount": str(Decimal(amount)),
        "currency": currency,
    }

    try:
        response = requests.post(settings.BOIPA_PAYMENT_URL, data=payload)
        logger.debug(f"Refund payload sent to BOIPA: {payload}")
        logger.debug(f"Raw response text from BOIPA: '{response.text.strip()}'")
        logger.debug(f"Response status code: {response.status_code}")
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error("BOIPA refund request failed: %s", e)
        return {
            "status_code": getattr(e.response, 'status_code', 500),
            "success": False,
            "error": str(e),
            "data": {},
        }

    try:
        data = response.json()
    except ValueError:
        logger.error("Invalid JSON response from BOIPA: %s", response.text)
        return {
            "status_code": response.status_code,
            "success": False,
            "error": "Invalid JSON response from BOIPA",
            "data": {"raw": response.text},
        }

    success = data.get("result") == "success"
    tx_refund_id = data.get("txId", None)

    # Optional: save refund to database if `order` and tx_refund_id are available
    from boipa.models import Refund
    if success and order and tx_refund_id:
        logger.info(f"Refund successful: Order #{order.id}, Refund TxID {tx_refund_id}")
        Refund.objects.create(
            order=order,
            tx_id=tx_refund_id,
            amount=Decimal(amount),
            raw_response=data,
        )

    return {
        "status_code": response.status_code,
        "success": success,
        "data": data,
        "refund_tx_id": tx_refund_id,
    }
