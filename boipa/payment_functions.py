import requests
import time
from decimal import Decimal
from django.urls import reverse
from django.conf import settings
import logging


payments_logger = logging.getLogger('payments')

def get_boipa_session_token(request, order_ref, total_price):
    try:
        amount = Decimal(f"{total_price:.2f}")
        ip_address = get_client_ip(request)
        url = settings.BOIPA_TOKEN_URL
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {
            "merchantId": settings.BOIPA_MERCHANT_ID,
            "password": settings.BOIPA_PASSWORD,
            "action": "PURCHASE",
            "timestamp": int(time.time() * 1000),
            "allowOriginUrl": settings.NGROK,
            "channel": "ECOM",
            "country": "IE",
            "currency": "EUR",
            "amount": str(amount),
            "merchantTxId": order_ref,
            "merchantLandingPageUrl": settings.NGROK + reverse('boipa:payment_response'),
            "merchantNotificationUrl": settings.NGROK + reverse('boipa:payment_notification'),
            "merchantLandingPageRedirectMethod": "GET",
            "userDevice": "DESKTOP",
            "customerIPAddress": ip_address,
            "merchantChallengeInd": "01",
            "merchantDecReqInd": "N",
            "freeText": "Optional extra transaction info",
            # New fields with dummy data
            'customerAddressStreet': "123 Fake Street",
            'customerAddressCity': "Dublin",
            'customerAddressPostalCode': "D02 X285",
        }

        payments_logger.debug("Sending payload to API: %s", {k: v for k, v in payload.items() if k != 'password'})
        response = requests.post(url, data=payload, headers=headers)
        if response.status_code == 200:
            return response.json().get('token')
        else:
            error_message = response.text
            payments_logger.error("Failed to obtain session token: HTTP Status %s: %s", response.status_code,
                                  error_message)
            # Handle specific HTTP errors e.g., 400, 401, 500, etc.
            handle_http_errors(response.status_code, error_message)
            return None
    except requests.RequestException as e:
        payments_logger.error("Network-related error when obtaining session token: %s", str(e))
        return None
    except Exception as e:
        payments_logger.error("Unexpected error when obtaining session token: %s", str(e))
        return None


def handle_http_errors(status_code, message):
    if status_code == 401:
        # Handle unauthorized error
        payments_logger.error("Authorization failed")
    elif status_code == 500:
        # Handle server error
        payments_logger.error("Server error encountered")
    # Additional specific error handling can be added here


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
