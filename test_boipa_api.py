import requests, time, json

MERCHANT_ID = "100121"
PASSWORD = "u0AYACBNI2643G87wk4o"
TOKEN_URL = "https://api.boipapaymentgateway.com/token"
PAYMENTS_URL = "https://api.boipapaymentgateway.com/payments"

tx_id = input("Enter txId or merchantTxId: ")

# Step 1: Get session token
payload_token = {
    "merchantId": MERCHANT_ID,
    "password": PASSWORD,
    "action": "GET_STATUS",
    "timestamp": int(time.time() * 1000),
}
token = requests.post(TOKEN_URL, data=payload_token).json().get("token")
if not token:
    print("❌ No token returned — check credentials or IP whitelist.")
    exit()

# Step 2: Request full transaction details
payload_status = {
    "merchantId": MERCHANT_ID,
    "token": token,
    "action": "GET_STATUS",
    "txId": tx_id,                # use txId if you have it — gives richer data
    "extendedResponse": "true",  # optional: some versions of API use this flag
}

resp = requests.post(PAYMENTS_URL, data=payload_status)
print(json.dumps(resp.json(), indent=4))
