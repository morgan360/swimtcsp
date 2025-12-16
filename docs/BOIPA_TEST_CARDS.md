# BOIPA Sandbox Test Cards

**Source:** BOIPA Developer Portal - Test Cards
**Environment:** Sandbox only (do NOT use in production)

---

## ✅ Successful Transaction Cards

Use these cards to simulate successful payments in the sandbox environment:

| Card Number | Card Type | Result | Code | Description |
|-------------|-----------|--------|------|-------------|
| `4263970000005262` | Visa | Successful | 00 | Successful transaction |
| `5425230000004415` | Mastercard | Successful | 00 | Successful transaction |
| `374101000000608` | American Express | Successful | 00 | Successful transaction |
| `36256000000725` | Diners Club | Successful | 00 | Successful transaction |
| `6011000000000087` | Discover | Successful | 00 | Successful transaction |
| `3566000000000000` | JCB | Successful | 00 | Successful transaction |
| `135400000007187` | UATP | Successful | 00 | Successful transaction |

---

## ❌ Declined Transaction Cards

Use these cards to test error handling and declined payment scenarios:

| Card Number | Card Type | Result | Code | Description |
|-------------|-----------|--------|------|-------------|
| `4000120000001154` | Visa | Declined | 101 | Declined by the bank |
| `4000130000001724` | Visa | Declined | 102 | Referral B |
| `4000160000004147` | Visa | Declined | 103 | Referral A - Card reported lost/stolen |
| `4009830000001985` | Visa | Declined | 200 | Communication Error |
| `4242420000000091` | Visa | Declined | 111 | Strong Customer Authentication Required |

---

## 💳 Card Details for Testing

When using test cards, you can use:

### Expiry Date
- **Any future date** - e.g., `12/25`, `01/26`, `06/27`

### CVV/CVC
- **Any 3 digits** for Visa, Mastercard, Discover, Diners Club - e.g., `123`, `456`, `789`
- **Any 4 digits** for American Express - e.g., `1234`, `5678`

### Cardholder Name
- **Any name** - e.g., `Test User`, `John Doe`, `Jane Smith`

### Billing Address (if required)
```
Street: 123 Main Street
City: Dublin
Postal Code: D02 X285
Country: IE (Ireland)
```

---

## 🔐 3D Secure Testing

### 3D Secure 2 Challenge Flow

When using cards that require 3D Secure authentication (like `4263970000005262`):

1. Card payment will redirect to 3D Secure authentication page
2. In sandbox, you may be asked to enter test authentication credentials
3. **Test 3DS Credentials (if prompted):**
   - Password: Any value
   - OTP: Any value
   - Or follow the on-screen test instructions

### Cards with 3D Secure
- `4263970000005262` - Visa with 3DS challenge
- Check BOIPA documentation for more 3DS test scenarios

---

## 📋 Testing Scenarios

### Test Case 1: Successful Payment
**Card:** `4263970000005262` (Visa)
**Expected:** Payment succeeds, order marked paid, enrollment created

### Test Case 2: Declined Payment
**Card:** `4000120000001154` (Visa)
**Expected:** Payment declined, order remains unpaid, no enrollment

### Test Case 3: Card Reported Lost/Stolen
**Card:** `4000160000004147` (Visa)
**Expected:** Payment declined with specific error code 103

### Test Case 4: Strong Customer Authentication Required
**Card:** `4242420000000091` (Visa)
**Expected:** 3D Secure authentication required

### Test Case 5: Communication Error
**Card:** `4009830000001985` (Visa)
**Expected:** Payment fails with communication error code 200

---

## 🚀 Quick Test Payment

### Recommended First Test:

1. **Use:** `4263970000005262` (Visa)
2. **Expiry:** `12/25`
3. **CVV:** `123`
4. **Name:** `Test User`
5. **Expected:** Successful payment with 3D Secure challenge

### Recommended Declined Test:

1. **Use:** `4000120000001154` (Visa)
2. **Expiry:** `12/25`
3. **CVV:** `123`
4. **Name:** `Test User`
5. **Expected:** Payment declined by bank (code 101)

---

## ⚠️ Important Notes

1. **Sandbox Only:** These cards only work in sandbox environment
2. **No Real Money:** All transactions are simulated
3. **No Billing:** Test cards will never be charged
4. **Expiry Dates:** Use any future date, sandbox doesn't validate
5. **CVV:** Any 3-digit (or 4-digit for Amex) number works
6. **Amount:** You can test any amount - even €0.01

---

## 🔍 Additional Test Scenarios

For more advanced testing scenarios, check:
- **BOIPA Developer Portal:** https://developer.boipagateway.com
- **Test Cards Section:** Resources → Test Cards
- **3D Secure Testing:** Look for "3D Secure test cards" documentation

---

## 📊 Response Codes Reference

| Code | Description |
|------|-------------|
| 00 | Successful transaction |
| 101 | Declined by the bank |
| 102 | Referral B |
| 103 | Referral A - Card reported lost/stolen |
| 111 | Strong Customer Authentication Required |
| 200 | Communication Error |

For complete list of response codes, see BOIPA API documentation.

---

## 🧪 Testing Checklist

- [ ] Test successful payment (Visa)
- [ ] Test successful payment (Mastercard)
- [ ] Test declined payment
- [ ] Test 3D Secure flow
- [ ] Test communication error
- [ ] Test webhook delivery
- [ ] Test duplicate webhook (idempotency)
- [ ] Test enrollment creation
- [ ] Test email notification

---

**Last Updated:** 2025-12-11
**Environment:** Sandbox Test Environment
**API Endpoint:** https://apis.sandbox.globalpay.com