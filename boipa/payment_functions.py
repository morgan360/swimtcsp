"""
BOIPA Payment Functions - NEW API (Dec 2025)

This module handles payment operations with the new BOIPA Developer Portal API.
Migrated from old IPG/Turnkey system to OAuth2-based authentication.
"""

import requests
import hashlib
import datetime
import time
from decimal import Decimal
from django.urls import reverse
from django.conf import settings
import logging


payments_logger = logging.getLogger('boipa')


def get_boipa_access_token():
    """
    Generate an OAuth2 access token for BOIPA API.

    Uses App ID + App Key with SHA512 signing.
    Tokens expire after 3600 seconds (1 hour).

    Returns:
        dict: Token data with 'token', 'expires_in', 'accounts', etc.
        None: If token generation fails
    """
    try:
        app_id = settings.BOIPA_APP_ID
        app_key = settings.BOIPA_APP_KEY

        # Step 1: Generate nonce (timestamp in ISO 8601 format)
        nonce = datetime.datetime.utcnow().isoformat() + "Z"

        # Step 2: Calculate secret (SHA512 hash of nonce + app_key)
        secret = hashlib.sha512((nonce + app_key).encode()).hexdigest()

        # Step 3: Request access token
        payload = {
            "app_id": app_id,
            "nonce": nonce,
            "secret": secret,
            "grant_type": "client_credentials"
        }

        headers = {
            "Content-Type": "application/json",
            "X-GP-Version": settings.BOIPA_API_VERSION
        }

        payments_logger.debug(f"Requesting access token from {settings.BOIPA_ACCESS_TOKEN_URL}")

        response = requests.post(
            settings.BOIPA_ACCESS_TOKEN_URL,
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            token_data = response.json()
            payments_logger.info(f"Access token obtained successfully, expires in {token_data.get('expires_in')}s")
            return token_data
        else:
            error_message = response.text
            payments_logger.error(
                f"Failed to obtain access token: HTTP {response.status_code}: {error_message}"
            )
            return None

    except Exception as e:
        payments_logger.exception(f"Unexpected error when obtaining access token: {str(e)}")
        return None


def create_hpp_payment_link(request, order_ref, total_price, payer_info=None):
    """
    Create a Hosted Payment Page (HPP) link for customer payment.

    Args:
        request: Django HTTP request object
        order_ref: Merchant order reference (e.g., "lessons_123")
        total_price: Amount in EUR (Decimal)
        payer_info: Optional dict with customer details (name, email, address)

    Returns:
        dict: Response with 'url' (HPP redirect URL), 'id' (link ID), etc.
        None: If link creation fails
    """
    try:
        # Step 1: Get access token
        token_data = get_boipa_access_token()
        if not token_data or 'token' not in token_data:
            payments_logger.error("Cannot create HPP link: failed to obtain access token")
            return None

        access_token = token_data['token']

        # Step 2: Prepare amount (convert to cents, no decimal point)
        amount = int(Decimal(f"{total_price:.2f}") * 100)

        # Step 3: Build base URL for callbacks
        base_url = settings.NGROK
        if base_url.endswith("tcsp.ie"):
            base_url = "https://www.tcsp.ie"

        # Step 4: Prepare payer information
        payer_data = {
            "name": payer_info.get('name', 'Customer') if payer_info else 'Customer',
            "language": "en",
            "email": payer_info.get('email', '') if payer_info else '',
        }

        # Add billing address if provided
        if payer_info and 'billing_address' in payer_info:
            payer_data['billing_address'] = payer_info['billing_address']
        else:
            # Default minimal address
            payer_data['billing_address'] = {
                "line_1": "123 Main Street",
                "line_2": "",
                "line_3": "",
                "city": "Dublin",
                "postal_code": "D02 X285",
                "country": "IE"
            }

        # Step 5: Prepare HPP link payload
        payload = {
            "account_name": settings.BOIPA_ACCOUNT_NAME,
            "type": "HOSTED_PAYMENT_PAGE",
            "name": f"Payment {order_ref}",
            "description": f"Payment for order {order_ref}",
            "reference": order_ref,
            "payer": payer_data,
            "order": {
                "amount": str(amount),
                "currency": "EUR",
                "reference": order_ref,
                "transaction_configuration": {
                    "channel": "CNP",
                    "country": "IE",
                    "capture_mode": "AUTO",
                    "allowed_payment_methods": ["CARD"]
                },
                "payment_method_configuration": {
                    "authentications": {
                        "preference": "CHALLENGE_PREFERRED"
                    }
                }
            },
            "notifications": {
                "return_url": base_url + reverse('boipa:payment_response'),
                "status_url": base_url + reverse('boipa:payment_notification'),
                "cancel_url": base_url + reverse('home')  # Where to go if user cancels
            },
            "usage_mode": "SINGLE",  # Link can only be used once
            "usage_limit": 1,
            "redirect_settings": {
                "auto_redirect": "ENABLED",  # Automatically redirect after payment
                "wait_time_seconds": 3  # Wait 3 seconds before redirecting
            }
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-GP-Version": settings.BOIPA_API_VERSION,
            "Accept": "application/json"
        }

        payments_logger.debug(f"Creating HPP link for order {order_ref}, amount €{total_price}")

        # Step 6: Create HPP link
        response = requests.post(
            settings.BOIPA_HPP_LINKS_URL,
            headers=headers,
            json=payload,
            timeout=15
        )

        if response.status_code == 200:
            link_data = response.json()
            hpp_url = link_data.get('url')
            link_id = link_data.get('id')
            payments_logger.info(f"HPP link created: {link_id}, URL: {hpp_url}")
            return link_data
        else:
            error_message = response.text
            payments_logger.error(
                f"Failed to create HPP link: HTTP {response.status_code}: {error_message}"
            )
            return None

    except Exception as e:
        payments_logger.exception(f"Unexpected error when creating HPP link: {str(e)}")
        return None


def get_client_ip(request):
    """
    Get client IP address from request.

    Args:
        request: Django HTTP request

    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def handle_http_errors(status_code, message):
    """
    Handle HTTP errors from BOIPA API.

    Args:
        status_code: HTTP status code
        message: Error message
    """
    if status_code == 401:
        payments_logger.error("Authorization failed - check App ID and App Key")
    elif status_code == 500:
        payments_logger.error("Server error encountered")
    else:
        payments_logger.error(f"HTTP {status_code}: {message}")


# ==========================================
# LEGACY FUNCTION - DEPRECATED
# Keep for reference during migration
# ==========================================

def get_boipa_session_token_OLD(request, order_ref, total_price):
    """
    DEPRECATED: Old IPG/Turnkey API token generation.
    This function is no longer used - kept for reference only.

    Use create_hpp_payment_link() instead for new BOIPA API.
    """
    payments_logger.warning(
        "DEPRECATED: get_boipa_session_token_OLD() called. "
        "This uses the old IPG/Turnkey API which is end-of-life. "
        "Use create_hpp_payment_link() instead."
    )
    return None