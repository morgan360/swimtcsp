# BOIPA Sandbox Testing Guide

## Overview
This guide walks you through testing the new BOIPA payment integration in the **sandbox environment** before deploying to production.

**Date Created:** 2025-12-11
**Status:** Ready for Testing

---

## Step 1: Create Sandbox Test App

### Actions Required:

1. **Go to:** https://developer.boipagateway.com (or https://developer.globalpay.com)
2. **Log in** with your BOIPA account
3. **Navigate to:** "Create an app (generate keys)"
4. **Create a new app:**
   - **App Name:** `TCSP Sandbox Test`
   - **Environment:** **SANDBOX** (very important!)
   - **Description:** `Test environment for TCSP payment integration`

5. **Generate keys** and copy the following:
   - Sandbox Merchant ID
   - Sandbox Client ID (if provided)
   - Sandbox Account Name
   - Sandbox App ID
   - Sandbox App Key

---

## Step 2: Configure Local Environment for Sandbox

### Update `.env` file:

1. **Comment out production credentials** (add `#` at start of each line):
   ```bash
   # BOIPA_MERCHANT_ID=IE7200018387978
   # BOIPA_CLIENT_ID=EVOIE0CHY0745
   # BOIPA_ACCOUNT_NAME=ECOMIE7200018387978
   # BOIPA_APP_ID=3rVzj4c9YTwOsBwU9d6wWfM6G2XfV2Dm
   # BOIPA_APP_KEY=TVo8VVsSu4JWb49s
   # BOIPA_API_BASE_URL=https://apis.boipagateway.com
   # BOIPA_ACCESS_TOKEN_URL=https://apis.boipagateway.com/ucp/accesstoken
   # BOIPA_HPP_LINKS_URL=https://apis.boipagateway.com/ucp/links
   # BOIPA_TRANSACTIONS_URL=https://apis.boipagateway.com/ucp/transactions
   ```

2. **Uncomment sandbox section** and add your sandbox credentials:
   ```bash
   BOIPA_MERCHANT_ID=YOUR_SANDBOX_MERCHANT_ID
   BOIPA_CLIENT_ID=YOUR_SANDBOX_CLIENT_ID
   BOIPA_ACCOUNT_NAME=YOUR_SANDBOX_ACCOUNT_NAME
   BOIPA_APP_ID=YOUR_SANDBOX_APP_ID
   BOIPA_APP_KEY=YOUR_SANDBOX_APP_KEY
   BOIPA_API_BASE_URL=https://apis.sandbox.globalpay.com
   BOIPA_ACCESS_TOKEN_URL=https://apis.sandbox.globalpay.com/ucp/accesstoken
   BOIPA_HPP_LINKS_URL=https://apis.sandbox.globalpay.com/ucp/links
   BOIPA_TRANSACTIONS_URL=https://apis.sandbox.globalpay.com/ucp/transactions
   ```

3. **Save** the `.env` file

---

## Step 3: Restart Django Development Server

```bash
# Stop current server (Ctrl+C)
# Then restart
python manage.py runserver
```

**Why?** Django needs to reload environment variables from the updated `.env` file.

---

## Step 4: Test Payment Flow

### Create a Test Order:

1. **Start local server:** `python manage.py runserver`
2. **Open browser:** http://localhost:8000
3. **Log in** as a test user
4. **Add a lesson/swim to cart**
5. **Proceed to checkout**
6. **Watch the logs** in your terminal for:
   - Access token generation
   - HPP link creation
   - Redirect to sandbox payment page

### Expected Flow:

```
Cart → Checkout → BOIPA Sandbox HPP → Enter Test Card → Payment Success → Webhook → Confirmation
```

---

## Step 5: Use Test Cards

BOIPA provides test card numbers for sandbox testing. Common test cards:

### Successful Payment (3D Secure Challenge):
- **Card Number:** `4263970000005262`
- **Expiry:** Any future date (e.g., `12/25`)
- **CVV:** Any 3 digits (e.g., `123`)
- **Cardholder Name:** Any name

### Declined Payment:
- **Card Number:** `4000120000001154`
- **Result:** Payment declined

### Other Test Scenarios:
Check BOIPA documentation for more test cards:
- https://developer.boipagateway.com → Resources → Test Cards

**3D Secure Testing:**
- When prompted for 3D Secure authentication in sandbox, use test credentials from BOIPA docs

---

## Step 6: Verify Webhook Delivery

### Check Logs:

Monitor `/logs/boipa.log` for webhook notifications:

```bash
tail -f logs/boipa.log
```

**Look for:**
- `📥 payment_notification view triggered`
- `📦 Parsed notification data: {...}`
- `✅ Order saved: id=..., paid=True`
- `📝 Payment notification record created`

### Expected Webhook Data:

```python
{
    'merchantTxId': 'lessons_123',  # Your order reference
    'txId': 'TRN_abc123...',        # BOIPA transaction ID
    'status': 'CAPTURED',           # Payment status
    'result': 'success',            # Result
    'amount': '5000',               # Amount in cents (€50.00)
    'currency': 'EUR',
    # ... other fields
}
```

---

## Step 7: Verify Database Updates

### Check Order Status:

```bash
python manage.py shell
```

```python
from lessons_orders.models import LessonOrder

# Find your test order
order = LessonOrder.objects.latest('id')
print(f"Order ID: {order.id}")
print(f"Paid: {order.paid}")  # Should be True
print(f"Transaction ID: {order.txId}")  # Should have BOIPA txId

# Check payment notification
from boipa.models import LessonOrderPaymentNotification
notification = LessonOrderPaymentNotification.objects.filter(order=order).first()
print(f"Notification Status: {notification.status}")
print(f"Notification TxId: {notification.txId}")
```

### Check Enrollment Creation:

```python
from lessons_bookings.models import LessonEnrollment

# Check if enrollment was created for the order
enrollments = LessonEnrollment.objects.filter(order=order)
print(f"Enrollments created: {enrollments.count()}")
for enrollment in enrollments:
    print(f"  - Swimling: {enrollment.swimling}, Lesson: {enrollment.lesson}")
```

---

## Step 8: Test Failed Payment

### Test Declined Card:

1. Go through checkout again
2. Use declined test card: `4000120000001154`
3. **Expected result:**
   - Payment fails on BOIPA page
   - User redirected back to failure page
   - Order remains `paid=False`
   - No enrollment created

### Verify:

```bash
# Check logs for failed payment
tail -f logs/boipa.log
# Should see "Payment not marked as paid"
```

---

## Step 9: Test Webhook Idempotency

### Simulate Duplicate Webhook:

BOIPA might send the same webhook multiple times. Test that your system handles this correctly.

**Manual Test:**
1. Complete a successful payment
2. Note the `txId` from logs
3. The system should ignore duplicate webhooks with same `txId`

**Check logs for:**
```
ℹ️ Duplicate notification ignored for order X, txId=TRN_abc123
```

---

## Step 10: Document Results

### Create Test Report:

Record your findings in `/docs/SANDBOX_TEST_RESULTS.md`:

```markdown
# Sandbox Test Results

**Date:** 2025-12-11
**Tester:** [Your name]

## Test Scenarios

### ✅ Test 1: Successful Lesson Payment
- Order ID: 123
- Amount: €50.00
- Card: 4263970000005262
- Result: SUCCESS
- Webhook received: YES
- Enrollment created: YES
- Email sent: YES

### ✅ Test 2: Failed Payment
- Order ID: 124
- Card: 4000120000001154
- Result: DECLINED
- Order marked paid: NO
- Enrollment created: NO

### ✅ Test 3: Webhook Idempotency
- Duplicate webhooks ignored: YES

## Issues Found

- [ ] None
- [ ] Issue 1: ...
- [ ] Issue 2: ...

## Ready for Production?

- [x] All tests passed
- [ ] Issues need fixing before production
```

---

## Step 11: Switch Back to Production

### When Testing Complete:

1. **Comment out sandbox credentials** in `.env`
2. **Uncomment production credentials**
3. **Restart Django server**
4. **Verify production URLs are active**

```bash
# Check which environment is active
python manage.py shell
```

```python
from django.conf import settings
print(settings.BOIPA_API_BASE_URL)
# Should print: https://apis.boipagateway.com (production)
# NOT: https://apis.sandbox.globalpay.com (sandbox)
```

---

## Troubleshooting

### Issue: Access token generation fails

**Check:**
- Sandbox App ID and App Key are correct
- API base URL is `https://apis.sandbox.globalpay.com`
- No typos in credentials

**Logs to check:**
```bash
tail -f logs/boipa.log | grep "access token"
```

### Issue: Webhook not received

**Check:**
- NGROK tunnel is running and URL in `.env` is current
- Status URL in HPP link includes full path: `https://xxx.ngrok-free.app/boipa/payment_notification/`
- CSRF exempt decorator on webhook view

**Test webhook manually:**
```bash
# Check if webhook endpoint is accessible
curl https://YOUR-NGROK-URL.ngrok-free.app/boipa/payment_notification/
# Should return 405 Method Not Allowed (expected - needs POST)
```

### Issue: 3D Secure authentication fails

**Check:**
- Using test card that requires 3D Secure: `4263970000005262`
- Follow BOIPA's 3D Secure test flow instructions
- Check if sandbox requires specific test credentials

### Issue: Order marked paid but no enrollment

**Check logs for:**
```bash
grep "Enrollment" logs/boipa.log
```

**Possible causes:**
- Exception in `handle_lessons_enrollment()` function
- Database constraint violation
- Missing related objects (Swimling, Lesson, Term)

---

## Key Differences: Sandbox vs Production

| Feature | Sandbox | Production |
|---------|---------|------------|
| API Base URL | `https://apis.sandbox.globalpay.com` | `https://apis.boipagateway.com` |
| Credentials | Separate sandbox App ID/Key | Production App ID/Key |
| Money | Fake transactions | Real money |
| 3D Secure | Test mode | Real authentication |
| Reporting | Test transactions visible | Real transactions |

---

## Next Steps After Sandbox Success

1. ✅ All sandbox tests pass
2. 📝 Document any issues and resolutions
3. 🔄 Update production settings files if needed
4. 🚀 Deploy to PythonAnywhere dev environment
5. 🧪 Test on dev with production credentials (optional)
6. ✨ Deploy to production
7. 📊 Monitor first real transactions closely

---

## Important Notes

- **Never commit** `.env` file with real credentials to git
- **Always test** in sandbox before production
- **Keep sandbox app** available for future testing
- **Monitor logs** closely during first production transactions
- **Have rollback plan** ready (old code available)

---

## Support & Resources

- **BOIPA Developer Portal:** https://developer.boipagateway.com
- **Test Cards:** https://developer.boipagateway.com/docs/resources/test-cards
- **API Reference:** https://developer.boipagateway.com/api
- **TCSP Payment Migration Doc:** `/docs/PAYMENT_MIGRATION.md`
- **BOIPA API Documentation:** `/docs/BOIPA_NEW_API_DOCUMENTATION.md`