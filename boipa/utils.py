# boipa/utils.py
import requests
from django.conf import settings
from decimal import Decimal
import logging

logger = logging.getLogger("boipa")


def _get_access_token():
    """Get OAuth2 access token using the new BOIPA API credentials."""
    import hashlib
    import datetime

    try:
        app_id = settings.BOIPA_APP_ID
        app_key = settings.BOIPA_APP_KEY
        nonce = datetime.datetime.utcnow().isoformat() + "Z"
        secret = hashlib.sha512((nonce + app_key).encode()).hexdigest()

        response = requests.post(
            settings.BOIPA_ACCESS_TOKEN_URL,
            headers={
                "Content-Type": "application/json",
                "X-GP-Version": getattr(settings, 'BOIPA_API_VERSION', '2021-03-22'),
            },
            json={
                "app_id": app_id,
                "nonce": nonce,
                "secret": secret,
                "grant_type": "client_credentials",
            },
            timeout=10,
        )

        if response.status_code == 200:
            return response.json().get('token')
        else:
            logger.error(f"Failed to get BOIPA access token: HTTP {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error getting BOIPA access token: {e}")
        return None


def verify_boipa_transaction(tx_id):
    """
    Verify a transaction with the BOIPA API.
    Supports both new API (TRN_ prefix) and legacy numeric txIds.
    Returns True if BOIPA confirms the transaction is captured.
    """
    if not tx_id:
        return False

    # New API: use OAuth2 + transactions endpoint
    if tx_id.startswith('TRN_') or hasattr(settings, 'BOIPA_APP_ID'):
        return _verify_new_api(tx_id)

    # Legacy fallback (old numeric txIds)
    return _verify_legacy_api(tx_id)


def _verify_new_api(tx_id):
    """Verify transaction using the new Global Payments / BOIPA API."""
    try:
        token = _get_access_token()
        if not token:
            return False

        transactions_url = getattr(settings, 'BOIPA_TRANSACTIONS_URL', '')
        if not transactions_url:
            logger.error("BOIPA_TRANSACTIONS_URL not configured")
            return False

        # The full txId (including appended reference) IS the transaction ID
        url = f"{transactions_url}/{tx_id}"
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-GP-Version": getattr(settings, 'BOIPA_API_VERSION', '2021-03-22'),
                "Accept": "application/json",
            },
            timeout=15,
        )

        if response.status_code == 200:
            data = response.json()
            status = data.get('status', '').upper()
            logger.info(f"BOIPA verify {tx_id}: status={status}")
            return status == 'CAPTURED'
        else:
            logger.error(f"BOIPA verify failed for {tx_id}: HTTP {response.status_code} {response.text[:200]}")
            return False
    except requests.Timeout:
        logger.error(f"BOIPA verify timed out for {tx_id}")
        return False
    except Exception as e:
        logger.error(f"BOIPA verify error for {tx_id}: {e}")
        return False


def _verify_legacy_api(tx_id):
    """Verify transaction using the old token-based BOIPA API."""
    import time

    try:
        merchant_id = getattr(settings, 'BOIPA_MERCHANT_ID', '')
        password = getattr(settings, 'BOIPA_PASSWORD', '')
        token_url = getattr(settings, 'BOIPA_TOKEN_URL', '')
        payments_url = getattr(settings, 'BOIPA_PAYMENT_URL', '')

        if not all([merchant_id, password, token_url, payments_url]):
            logger.warning("Legacy BOIPA API settings not configured, cannot verify")
            return False

        token_data = requests.post(token_url, data={
            "merchantId": merchant_id,
            "password": password,
            "action": "GET_STATUS",
            "timestamp": int(time.time() * 1000),
        }, timeout=10).json()

        token = token_data.get("token")
        if not token:
            return False

        status_data = requests.post(payments_url, data={
            "merchantId": merchant_id,
            "token": token,
            "action": "GET_STATUS",
            "txId": tx_id,
        }, timeout=10).json()

        return status_data.get("status") == "CAPTURED"
    except Exception as e:
        logger.error(f"Legacy BOIPA verify error for {tx_id}: {e}")
        return False


def refund_boipa_transaction(tx_id, amount, currency="EUR", order=None):
    """Send a refund request to the BOIPA Gateway."""
    merchant_id = getattr(settings, 'BOIPA_MERCHANT_ID', '')
    password = getattr(settings, 'BOIPA_PASSWORD', '')
    payments_url = getattr(settings, 'BOIPA_PAYMENT_URL', '')

    payload = {
        "merchantId": merchant_id,
        "password": password,
        "action": "REFUND",
        "txId": tx_id,
        "amount": str(Decimal(amount)),
        "currency": currency,
    }

    try:
        response = requests.post(payments_url, data=payload, timeout=15)
        logger.debug(f"Refund payload sent to BOIPA: {payload}")
        logger.debug(f"Raw response text from BOIPA: '{response.text.strip()}'")
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