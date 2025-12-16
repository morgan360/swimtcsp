# BOIPA New API Integration Documentation

**Date:** December 11, 2025
**Status:** In Progress - Gathering API Documentation
**Purpose:** Migration from OLD IPG/Turnkey system to NEW BOIPA Developer Portal API

---

## 🔑 Production Credentials (LIVE)

**Received:** December 8, 2025
**Source:** Emails from Angelica Miranda (BOIPA Support)

### API Credentials
- **Merchant ID:** `IE7200018387978`
- **Client ID:** `EVOIE0CHY0745`
- **Account Name:** `ECOMIE7200018387978`
- **App ID:** `3rVzj4c9YTwOsBwU9d6wWfM6G2XfV2Dm`
- **App Key:** `TVo8VVsSu4JWb49s` (Full key: part1 + part2 from two separate emails)

### Portal Access
- **Reporting Portal:** https://portal.boipagateway.com
  - Username: `TempSwimPool`
  - Password: `T3mpSwimP00l2025`
  - Client ID: `EVOIE0CHY0745`

- **Developer Portal:** https://developer.boipagateway.com
  - Documentation and API reference

- **Business Resource Centre (BRC):** https://boipa.com/business
  - View statements, invoices, billing, transaction reports

---

## 📚 API Documentation Discovered

### Base URLs
- **API Base:** `https://apis.boipagateway.com`
- **Access Token Endpoint:** `https://apis.boipagateway.com/ucp/accesstoken`
- **Developer Docs:** https://developer.boipagateway.com/api/references-overview

### API Version
- **X-GP-Version:** `2021-03-22` (required header)

---

## 🔐 Authentication Flow (OAuth-style)

### Overview
The new BOIPA API uses **OAuth2 client credentials** flow with HMAC-SHA512 signing.

**Key Change from OLD API:**
- ❌ OLD: `merchantId` + `password` sent directly in requests
- ✅ NEW: `app_id` + `app_key` → generate access token → use token in subsequent requests

### Step-by-Step Authentication

#### **Step 1: Obtain App Credentials**
Already have:
- `app_id` = `3rVzj4c9YTwOsBwU9d6wWfM6G2XfV2Dm`
- `app_key` = `TVo8VVsSu4JWb49s`

#### **Step 2: Create Random Nonce Value**
Generate a unique nonce (typically a timestamp in ISO 8601 format):
```python
import datetime
nonce = datetime.datetime.utcnow().isoformat() + "Z"
# Example: "2029-03-14T13:24:10.832Z"
```

#### **Step 3: Calculate Secret Key**
Create SHA512 hash of `nonce + app_key`:
```python
import hashlib

nonce = "2029-03-14T13:24:10.832Z"
app_key = "TVo8VVsSu4JWb49s"

# Concatenate nonce + app_key
message = nonce + app_key
# Example: "2029-03-14T13:24:10.832ZTVo8VVsSu4JWb49s"

# SHA512 hash
secret = hashlib.sha512(message.encode()).hexdigest()
```

⚠️ **IMPORTANT:** Never send `app_key` directly in requests. Always hash it.

#### **Step 4: Call the Access Token Endpoint**

**Request:**
```http
POST https://apis.boipagateway.com/ucp/accesstoken
Content-Type: application/json
X-GP-Version: 2021-03-22

{
  "app_id": "3rVzj4c9YTwOsBwU9d6wWfM6G2XfV2Dm",
  "nonce": "2029-03-14T13:24:10.832Z",
  "secret": "<SHA512_HASH_FROM_STEP_3>",
  "grant_type": "client_credentials"
}
```

**Python Example:**
```python
import requests
import hashlib
import datetime

# Credentials
app_id = "3rVzj4c9YTwOsBwU9d6wWfM6G2XfV2Dm"
app_key = "TVo8VVsSu4JWb49s"

# Generate nonce (timestamp)
nonce = datetime.datetime.utcnow().isoformat() + "Z"

# Calculate secret
secret = hashlib.sha512((nonce + app_key).encode()).hexdigest()

# Request access token
response = requests.post(
    "https://apis.boipagateway.com/ucp/accesstoken",
    headers={
        "Content-Type": "application/json",
        "X-GP-Version": "2021-03-22"
    },
    json={
        "app_id": app_id,
        "nonce": nonce,
        "secret": secret,
        "grant_type": "client_credentials"
    }
)

token_data = response.json()
```

#### **Step 5: Receive Access Token Response**

**Response Format:**
```json
{
  "accounts": [
    {
      "id": "TRA_34b9806b35bd4012bd23206a00abc1a1",
      "name": "API",
      "permissions": [
        "BAT_PUT_Close",
        "TRN_POST_Adjustment",
        "TRN_POST_Authorize",
        "TRN_POST_Capture",
        "TRN_POST_Force",
        "TRN_POST_Initiate",
        "TRN_POST_Reauthorize",
        "TRN_POST_Refund",
        "TRN_POST_Refund_Standalone",
        "TRN_POST_Reverse",
        "TRN_POST_Verify"
      ]
    }
  ],
  "token": "<ACCESS_TOKEN_STRING>",
  "type": "Bearer",
  "expires_in": 3600,
  "scope": "..."
}
```

**Key Fields:**
- `token` - The access token to use in Authorization header
- `type` - "Bearer" (token type)
- `expires_in` - Token lifetime in seconds (typically 3600 = 1 hour)
- `permissions` - What actions this token can perform

#### **Step 6: Use Access Token in Subsequent Requests**

For all payment API calls, include:
```http
Authorization: Bearer <ACCESS_TOKEN>
X-GP-Version: 2021-03-22
Content-Type: application/json
```

---

## 🔄 Key Differences: OLD vs NEW API

| Feature | OLD API (IPG/Turnkey) | NEW API (BOIPA Developer Portal) |
|---------|----------------------|----------------------------------|
| **Authentication** | `merchantId` + `password` in body | OAuth2 access token via signed request |
| **Merchant ID** | `100121` (sandbox) | `IE7200018387978` (production) |
| **API Keys** | Password: `qWGEJQQAkhROSTGpwS5O` | App ID + App Key |
| **Token Endpoint** | `https://apiuat.test.boipapaymentgateway.com/token` | `https://apis.boipagateway.com/ucp/accesstoken` |
| **Security** | Direct password transmission | HMAC-SHA512 signing |
| **Token Lifetime** | Unknown | 3600 seconds (1 hour) |
| **Headers** | `Content-Type: application/x-www-form-urlencoded` | `Content-Type: application/json` + `X-GP-Version` |
| **Status** | ❌ End-of-life, discontinued | ✅ Active, production-ready |

---

## 📋 Environment Variables

Updated `.env` file with new credentials:

```bash
# NEW BOIPA Production Credentials (Dec 2025)
BOIPA_MERCHANT_ID=IE7200018387978
BOIPA_CLIENT_ID=EVOIE0CHY0745
BOIPA_ACCOUNT_NAME=ECOMIE7200018387978
BOIPA_APP_ID=3rVzj4c9YTwOsBwU9d6wWfM6G2XfV2Dm
BOIPA_APP_KEY=TVo8VVsSu4JWb49s

# New API Endpoints
BOIPA_API_BASE_URL=https://apis.boipagateway.com
BOIPA_ACCESS_TOKEN_URL=https://apis.boipagateway.com/ucp/accesstoken
BOIPA_DEVELOPER_PORTAL=https://developer.boipagateway.com
BOIPA_REPORTING_PORTAL=https://portal.boipagateway.com
```

---

## 💳 Transaction Creation API

### **Create Transaction (Sale/Refund) Endpoint**

**Purpose:** Create a Sale or Refund transaction to transfer funds between Payer and Merchant.

#### **Endpoints:**
- **Production:** `POST https://apis.boipagateway.com/ucp/transactions`
- **Sandbox:** `POST https://apis.sandbox.boipagateway.com/ucp/transactions`

#### **Required Headers:**
```http
Authorization: Bearer <ACCESS_TOKEN>
X-GP-Version: 2021-03-22
Content-Type: application/json
Accept: application/json
X-GP-Idempotency: <UNIQUE_STRING>  (optional but recommended)
```

**Note:** `X-GP-Idempotency` prevents duplicate transactions if same value used within 24 hours.

#### **Required Request Parameters:**

```json
{
  "account_name": "transaction_processing",
  "type": "SALE",
  "channel": "CNP",
  "country": "IE",
  "amount": "1999",
  "currency": "EUR",
  "reference": "93469c78-f3f9-427c-84df-ca0584bb58bf",
  "payment_method": {
    "name": "James Mason",
    "entry_mode": "ECOM",
    "card": {
      "number": "4111111111111111",
      "expiry_month": "12",
      "expiry_year": "25",
      "cvv": "123"
    }
  }
}
```

#### **Key Parameters Explained:**

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `account_name` | string | ✅ | Account identifier | `"transaction_processing"` |
| `type` | string | ✅ | Transaction type | `"SALE"` or `"REFUND"` |
| `channel` | string | ✅ | Transaction channel | `"CNP"` (Customer Not Present) or `"CP"` |
| `country` | string | ✅ | Merchant country (ISO-3166-1 alpha-2) | `"IE"` for Ireland |
| `amount` | string | ✅ | Amount in smallest denomination (cents) | `"1999"` = €19.99 |
| `currency` | string | ✅ | Currency (ISO-4217 alpha-3) | `"EUR"` |
| `reference` | string | ✅ | Merchant transaction reference | `"lessons_123"` |
| `capture_mode` | string | ❌ | When to capture funds | `"AUTO"` (default), `"LATER"`, `"MULTIPLE"` |
| `payment_method` | object | ✅ | Payment method details | See below |

#### **Optional Parameters:**
- `capture_mode`: `"AUTO"` (default), `"LATER"`, `"MULTIPLE"`, `"LATER_FINAL"`
- `gratuity_amount`: Tip amount
- `description`: Transaction description
- `ip_address`: Customer IP address
- `payer_reference`: Customer reference
- `notifications`: Webhook URLs for status updates
- `payer`: Customer details (name, email, etc.)

#### **Response Format:**

**Success (200):**
```json
{
  "id": "TRN_uzFr7t4VOqxdLDI44hHmXIjHtOOE8d",
  "time_created": "2026-05-03T21:23:39.718Z",
  "type": "SALE",
  "status": "CAPTURED",
  "channel": "CNP",
  "capture_mode": "AUTO",
  "amount": "1999",
  "currency": "EUR",
  "country": "IE",
  "merchant_id": "MER_A6A1EC44522F96630ABEA17A",
  "merchant_name": "ABC INDUSTRIES",
  "account_id": "TRA_86920f927028745yt34d077d88beb29b",
  "account_name": "transaction_processing",
  "reference": "becf9f3e-4d33-459c-8ed2-0c4affc9555e",
  "payment_method": { ... },
  "payer": { ... }
}
```

#### **Transaction Status Values:**

| Status | Meaning |
|--------|---------|
| `CAPTURED` | Successfully authorized and captured, funding will commence |
| `PREAUTHORIZED` | Approved but requires capture request |
| `PENDING` | Sent to payment provider, awaiting result |
| `INITIATED` | Successfully initiated, awaiting async notification |
| `DECLINED` | Payment provider declined transaction |
| `REVERSED` | Transaction voided/cancelled before funding |
| `FAILED` | Error after successful creation |
| `REJECTED` | Transfer rejected during funding process |
| `FUNDED` | Funds successfully transferred |
| `FOR_REVIEW` | Requires review before authorization |

---

## 🔍 Refund API

**Endpoint:** Same as transaction creation, but with `type: "REFUND"`

```json
POST https://apis.boipagateway.com/ucp/transactions
{
  "account_name": "transaction_processing",
  "type": "REFUND",
  "channel": "CNP",
  "country": "IE",
  "amount": "1999",
  "currency": "EUR",
  "reference": "refund_123",
  "payment_method": { ... }
}
```

**Note:** Standalone refunds (not linked to previous sale) depend on live configuration.

---

## 🌐 Hosted Payment Page (HPP) Integration ⭐ CRITICAL

### **Overview**
The HPP allows customers to enter their payment details on a secure BOIPA-hosted page instead of your website. This is our **current payment flow**.

### **HPP Flow:**
1. Create an access token (OAuth)
2. Create a payment link with order details
3. Redirect customer to the HPP URL returned
4. Customer enters card details on BOIPA's secure page
5. BOIPA processes payment
6. Customer redirected back to your `return_url`
7. BOIPA sends webhook to your `status_url`

---

### **Step 1: Create HPP Link**

**Endpoint:**
- **Production:** `POST https://apis.boipagateway.com/ucp/links`
- **Sandbox:** `POST https://apis.sandbox.boipagateway.com/ucp/links`

**Required Headers:**
```http
Authorization: Bearer <ACCESS_TOKEN>
X-GP-Version: 2021-03-22
Content-Type: application/json
Accept: application/json
```

**Request Body:**
```json
{
   "account_name": "transaction_processing",
   "type": "HOSTED_PAYMENT_PAGE",
   "name": "Swim Lesson Payment",
   "description": "Spring Term 2025 Lessons",
   "reference": "lessons_order_123",
   "payer": {
      "name": "James Mason",
      "language": "en",
      "email": "customer@example.com",
      "mobile_phone": {
         "country_code": "353",
         "subscriber_number": "831234567"
      },
      "billing_address": {
         "line_1": "123 Main Street",
         "line_2": "",
         "line_3": "",
         "city": "Dublin",
         "postal_code": "D02 X285",
         "country": "IE"
      }
   },
   "order": {
      "amount": "19900",
      "currency": "EUR",
      "reference": "order-645",
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
      "return_url": "https://www.tcsp.ie/boipa/payment-response/",
      "status_url": "https://www.tcsp.ie/boipa/payment-notification/"
   }
}
```

**Key Parameters:**

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `account_name` | ✅ | Account identifier | `"transaction_processing"` |
| `type` | ✅ | Link type | `"HOSTED_PAYMENT_PAGE"` |
| `reference` | ✅ | Merchant order reference | `"lessons_123"` |
| `order.amount` | ✅ | Amount in cents | `"19900"` = €199.00 |
| `order.currency` | ✅ | Currency code | `"EUR"` |
| `order.transaction_configuration.channel` | ❌ | Transaction channel | `"CNP"` |
| `order.transaction_configuration.country` | ❌ | Merchant country | `"IE"` |
| `order.transaction_configuration.capture_mode` | ❌ | Capture mode | `"AUTO"` (default) |
| `notifications.return_url` | ❌ | User redirect after payment | `"https://www.tcsp.ie/boipa/payment-response/"` |
| `notifications.status_url` | ❌ | Webhook URL for status updates | `"https://www.tcsp.ie/boipa/payment-notification/"` |
| `payer.name` | ❌ | Customer name | `"John Doe"` |
| `payer.email` | ❌ | Customer email | `"john@example.com"` |
| `payer.billing_address` | Recommended | Billing address | See example above |

**Important Notes:**
- HPP links expire after **24 hours**
- `usage_mode` is always `"SINGLE"` for HPP
- `usage_limit` is always `1` for HPP
- Payer can be `NEW` or `ACTIVE` (for stored cards)

---

### **Step 2: Response - Get HPP URL**

**Success Response (200):**
```json
{
   "id": "LNK_JGWfx9L9Oc3RS2N5WobbocjMDuSqvm",
   "account_name": "transaction_processing",
   "url": "https://apis.sandbox.boipagateway.com/ucp/hpp/redirect/42060877-8bf9-4ae3-a3ae-99a6da10cf41",
   "status": "ACTIVE",
   "type": "HOSTED_PAYMENT_PAGE",
   "usage_mode": "SINGLE",
   "usage_limit": "1",
   "name": "Mobile Bill Payment",
   "description": "February and March Invoice",
   "expiration_date": "2024-06-11T14:09:23.577Z",
   "order": {
      "amount": "1000",
      "currency": "EUR",
      "reference": "order-645"
   },
   "action": {
      "id": "ACT_JGWfx9L9Oc3RS2N5WobbocjMDuSqvm",
      "type": "LINK_CREATE",
      "time_created": "2024-06-10T14:09:23.577Z",
      "result_code": "SUCCESS"
   }
}
```

**Critical Field:**
```python
hpp_url = response_data['url']
# Example: "https://apis.sandbox.boipagateway.com/ucp/hpp/redirect/42060877-8bf9-4ae3-a3ae-99a6da10cf41"
```

**Production HPP URL Pattern:**
- Sandbox: `https://apis.sandbox.boipagateway.com/ucp/hpp/redirect/{UUID}`
- Production: `https://apis.boipagateway.com/ucp/hpp/redirect/{UUID}`

---

### **Step 3: Redirect Customer to HPP**

After receiving the response, redirect the user to the `url` field:

```python
# In Django view
hpp_url = response.json()['url']
return redirect(hpp_url)
```

The customer will:
1. See BOIPA's secure payment page
2. Enter their card details
3. Complete 3D Secure authentication if required
4. Be redirected back to your `return_url`

---

### **Step 4: Handle Return URL (User Redirect)**

After payment, user is redirected to your `return_url` with query parameters:

**Example:**
```
https://www.tcsp.ie/boipa/payment-response/?reference=lessons_123&status=CAPTURED
```

**Query Parameters:**
- `reference` - Your order reference
- `status` - Transaction status (`CAPTURED`, `DECLINED`, etc.)

---

### **Step 5: Handle Webhook (Status URL)**

BOIPA sends a webhook POST to your `status_url` with transaction details:

**Webhook Payload:** (Similar to current webhook format, needs verification)
```json
{
   "id": "TRN_abc123",
   "status": "CAPTURED",
   "amount": "19900",
   "currency": "EUR",
   "reference": "lessons_123",
   ...
}
```

**Important:** Your webhook handler should:
1. Verify the webhook authenticity (signature check if provided)
2. Mark order as paid
3. Create enrollments
4. Send confirmation email
5. Return 200 OK

---

## 📦 Still Need to Verify:

1. **Webhook Signature Verification**
   - Does new API sign webhooks?
   - How to verify webhook authenticity?

2. **Webhook Payload Format**
   - Exact structure of status_url webhook
   - All fields included

3. **Error Handling**
   - Error response formats
   - How to handle failed HPP link creation

---

## 📞 Support Contacts

**BOIPA eCommerce Support:**
- Email: ecommerce@boipa.com
- Phone: 1800 806 670
- Support Ticket: BOIPA-6789

**Support Resources:**
- Developer Documentation: https://developer.boipagateway.com
- Integration Guides: https://developer.boipagateway.com/docs/integration-options/overview
- User Management: https://www.boipa.com/en-ie/user-management
- Payment Support: https://www.boipa.com/en-ie/online-in-app-phone-payments-support

---

## 📝 Migration Timeline

- **April 24, 2025:** Initial migration notice sent
- **December 8, 2025:** Production credentials received
- **December 11, 2025:** Documentation gathering in progress
- **TBD:** Old IPG/Turnkey system shutdown date (UNKNOWN - URGENT)

---

## ⚠️ Critical Notes

1. **Old System End-of-Life:** The IPG/Turnkey system "will be discontinued and will no longer accept online payments" - exact date unknown
2. **Security:** Never commit `app_key` to git - keep in `.env` only
3. **Token Expiration:** Access tokens expire after 1 hour - must implement refresh logic
4. **Testing:** Need to verify integration works before old system shuts down

---

## 🔍 Code Changes Required

### Files to Update:
- `/boipa/payment_functions.py` - Rewrite token generation
- `/boipa/views.py` - Update payment session initiation
- `/boipa/utils.py` - Update verification and refund functions
- `/config/local_settings.py` - Add new environment variables
- `/config/development_settings.py` - Add new environment variables
- `/config/production_settings.py` - Add new environment variables

### New Functions Needed:
- `get_boipa_access_token()` - Generate OAuth access token
- `create_payment_session()` - Create payment with new API
- `verify_webhook_signature()` - Validate webhook authenticity (if required)

---

**Last Updated:** December 11, 2025
**Next Action:** Find Transaction/Payment creation endpoint in API documentation