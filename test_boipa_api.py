"""Ad-hoc lookup of a BOIPA transaction, for support and reconciliation queries.

Run it directly, never imported:

    python test_boipa_api.py <txId or merchantTxId>

It targets the legacy (pre-December-2025) gateway, whose settings are commented
out in config/*_settings.py — the site itself now uses the Developer Portal API.
Keep it only for as long as old transactions still need looking up.

Credentials come from .env (BOIPA_MERCHANT_ID, BOIPA_PASSWORD); they are never
written into this file, which is committed to a public repository.
"""
import json
import sys
import time

import requests
from decouple import config

TOKEN_URL = config("BOIPA_TOKEN_URL", default="https://api.boipapaymentgateway.com/token")
PAYMENTS_URL = config("BOIPA_PAYMENT_URL", default="https://api.boipapaymentgateway.com/payments")


def get_token(merchant_id, password):
    response = requests.post(
        TOKEN_URL,
        data={
            "merchantId": merchant_id,
            "password": password,
            "action": "GET_STATUS",
            "timestamp": int(time.time() * 1000),
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("token")


def get_status(merchant_id, token, tx_id):
    response = requests.post(
        PAYMENTS_URL,
        data={
            "merchantId": merchant_id,
            "token": token,
            "action": "GET_STATUS",
            "txId": tx_id,           # txId gives richer data than merchantTxId
            "extendedResponse": "true",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main(argv):
    merchant_id = config("BOIPA_MERCHANT_ID", default="")
    password = config("BOIPA_PASSWORD", default="")
    if not merchant_id or not password:
        print("❌ Set BOIPA_MERCHANT_ID and BOIPA_PASSWORD in .env first.")
        return 1

    tx_id = argv[0] if argv else input("Enter txId or merchantTxId: ").strip()
    if not tx_id:
        print("❌ No transaction id given.")
        return 1

    token = get_token(merchant_id, password)
    if not token:
        print("❌ No token returned — check the credentials or the IP whitelist.")
        return 1

    print(json.dumps(get_status(merchant_id, token, tx_id), indent=4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
