# boipa/utils.py
import re
import time

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


# BOIPA transaction ids look like TRN_nxP3BxRKhPOypvXG0H8C5WY_5_1795304199. Anything
# else is refused before it is put into the API URL alongside our bearer token.
TX_ID_FORMAT = re.compile(r"[A-Za-z0-9_-]{1,100}")

# BOIPA calls payment-response about 100 ms after creating the transaction, and
# its lookup API can still say INITIATED at that point (a real €312 lesson
# payment, 22 Nov 2026 10:59). A transaction that is ours but still processing
# is asked about again, for up to about 10 seconds in all, before it counts as
# unpaid. Forgeries never get here: BOIPA has no record of them.
STILL_PROCESSING = {"INITIATED", "PENDING", "PREAUTHORIZED", "PROCESSING", ""}
CAPTURE_WAITS = (0.5, 1, 1.5, 2, 2, 3)


def _order_key(reference):
    """('swims', 103466) from 'swims_103466_1795342279', or None."""
    parts = str(reference or "").split("_")
    if len(parts) < 2:
        return None
    try:
        return parts[0], int(parts[1])
    except ValueError:
        return None


def confirm_payment(tx_id, merchant_tx_id):
    """Ask BOIPA whether `tx_id` is a captured payment for this order.

    Returns (ok, reason). The payment callbacks used to believe whatever they
    were sent, so anyone could mark an order paid by posting status=CAPTURED with
    its reference (done to a real customer's order on 22 Nov 2026). Now an order
    is only marked paid when BOIPA itself says the transaction was captured, and
    for this order: BOIPA's own record carries the reference we gave it, so a
    real €7 swim payment cannot be replayed against a €300 lesson order.

    A transaction that is ours but still INITIATED is asked about again for a
    few seconds, because BOIPA calls back before its own record catches up.

    Fails closed. If BOIPA cannot be reached the order stays unpaid and staff are
    told, rather than a forged message getting through during an outage.
    """
    if not isinstance(tx_id, str) or not TX_ID_FORMAT.fullmatch(tx_id):
        return False, "malformed transaction id"
    ours = _order_key(merchant_tx_id)
    if not ours:
        return False, "malformed order reference"
    for attempt, delay in enumerate((0,) + CAPTURE_WAITS):
        if delay:
            time.sleep(delay)
        details = _fetch_new_api(tx_id)
        if details is None:
            return False, "BOIPA has no record of this transaction, or could not be reached"
        raw = details.get("raw") or {}
        theirs_ref = raw.get("reference") or raw.get("order_reference")
        if _order_key(theirs_ref) != ours:
            return False, f"BOIPA's transaction is for {theirs_ref!r}, not {merchant_tx_id!r}"
        if details["captured"]:
            return True, ""
        if details["status"] not in STILL_PROCESSING:
            break
        logger.info(f"BOIPA {tx_id} still {details['status']}, asking again (attempt {attempt + 1})")
    return False, f"BOIPA status is {details['status'] or 'blank'}, not CAPTURED"


def get_boipa_transaction_details(tx_id):
    """
    Get full transaction details from BOIPA API.
    Returns dict with 'captured', 'status', 'amount', 'currency' or None on error.
    """
    if not tx_id:
        return None

    if tx_id.startswith('TRN_') or hasattr(settings, 'BOIPA_APP_ID'):
        return _fetch_new_api(tx_id)

    return None


def _fetch_new_api(tx_id):
    """Fetch transaction details from the new Global Payments / BOIPA API.
    Returns dict with 'captured', 'status', 'amount', 'currency' or None on error."""
    try:
        token = _get_access_token()
        if not token:
            return None

        transactions_url = getattr(settings, 'BOIPA_TRANSACTIONS_URL', '')
        if not transactions_url:
            logger.error("BOIPA_TRANSACTIONS_URL not configured")
            return None

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
            amount_str = data.get('amount', None)
            # BOIPA API returns amounts in minor units (cents), convert to euros
            amount = Decimal(amount_str) / Decimal('100') if amount_str else None
            currency = data.get('currency', '')
            logger.info(f"BOIPA verify {tx_id}: status={status} amount={amount} currency={currency}")
            return {
                'captured': status == 'CAPTURED',
                'status': status,
                'amount': amount,
                'currency': currency,
                'raw': data,
            }
        else:
            logger.error(f"BOIPA verify failed for {tx_id}: HTTP {response.status_code} {response.text[:200]}")
            return None
    except requests.Timeout:
        logger.error(f"BOIPA verify timed out for {tx_id}")
        return None
    except Exception as e:
        logger.error(f"BOIPA verify error for {tx_id}: {e}")
        return None


def _verify_new_api(tx_id):
    """Verify transaction using the new Global Payments / BOIPA API."""
    result = _fetch_new_api(tx_id)
    if result is None:
        return False
    return result['captured']


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