# BOIPA New API - Troubleshooting Guide

**Last Updated:** December 16, 2025

---

## 🚨 Common Issues and Solutions

### 1. Blank Page After Payment

**Symptoms:**
- User completes payment on BOIPA
- Sees blank white page
- Payment may or may not have processed

**Diagnosis:**
Check logs for `SessionInterrupted` exception:
```bash
tail -f ~/swimtcsp/logs/payments.log | grep SessionInterrupted
```

**Causes & Solutions:**

#### A. Missing NGROK Variable
**Error in logs:** No payment_response logs at all
**Fix:**
```bash
# Add to .env
NGROK=https://www.tcsp.ie  # or your domain, NO trailing slash
```

#### B. SessionInterrupted Error
**Error in logs:** `django.contrib.sessions.exceptions.SessionInterrupted`
**Fix:** Ensure `PaymentGatewaySessionMiddleware` is in middleware stack

Check `config/base_settings.py`:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'utils.middleware.PaymentGatewaySessionMiddleware',  # Must be here!
    ...
]
```

#### C. Trailing Slash in NGROK
**Error:** BOIPA can't reach callback URL
**Fix:**
```bash
# WRONG
NGROK=https://www.tcsp.ie/

# RIGHT
NGROK=https://www.tcsp.ie
```

---

### 2. Payment Not Processing (Order Stays Unpaid)

**Symptoms:**
- User completes payment
- Money taken from card
- Order in database shows `paid=False`
- No enrollment created
- No email sent

**Diagnosis:**
```bash
# Check if payment_response was called
tail -f ~/swimtcsp/logs/payments.log | grep "payment_response"

# Check for errors during processing
tail -f ~/swimtcsp/logs/payments.log | grep "ERROR"
```

**Common Causes:**

#### A. JSON Parsing Failed
**Error:** `Failed to parse JSON body`
**Check:** Is `@csrf_exempt` decorator present?
```python
# boipa/views.py line 62
@csrf_exempt
def payment_response(request):
```

#### B. Wrong Order Reference Format
**Error:** `Invalid merchantTxId format`
**Check:** Order reference should be `lesson_123` or `swims_456` format

#### C. Order Not Found
**Error:** `Order X not found`
**Check database:**
```python
from lessons_orders.models import Order
Order.objects.get(id=X)
```

---

### 3. CSRF 403 Forbidden Error

**Symptoms:**
- User redirected to BOIPA
- Completes payment
- Sees "403 Forbidden (CSRF cookie not set.)"

**Solution:**
Ensure payment endpoints have `@csrf_exempt` decorator:

```python
# boipa/views.py
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def payment_response(request):
    ...

@csrf_exempt
def payment_notification(request):
    ...
```

---

### 4. OAuth2 Token Generation Fails

**Symptoms:**
- User tries to checkout
- Error: "Unable to create payment link"
- Logs show: `Failed to obtain access token`

**Diagnosis:**
```bash
tail -f ~/swimtcsp/logs/payments.log | grep "access token"
```

**Common Causes:**

#### A. Wrong Credentials
**Check `.env` file:**
```bash
# Sandbox
BOIPA_APP_ID=C1vHe0PqBzH4ukGANlHW5xAG1jeNpgFu
BOIPA_APP_KEY=QSptsGy9TgzTf9Nf

# Production
BOIPA_APP_ID=3rVzj4c9YTwOsBwU9d6wWfM6G2XfV2Dm
BOIPA_APP_KEY=TVo8VVsSu4JWb49s
```

#### B. Wrong API URL
**Check `.env`:**
```bash
# Sandbox
BOIPA_ACCESS_TOKEN_URL=https://apis.sandbox.globalpay.com/ucp/accesstoken

# Production
BOIPA_ACCESS_TOKEN_URL=https://apis.boipagateway.com/ucp/accesstoken
```

#### C. SHA512 Signing Error
**Check:** `boipa/payment_functions.py` lines 36-40
```python
nonce = datetime.datetime.utcnow().isoformat() + "Z"
secret = hashlib.sha512((nonce + app_key).encode()).hexdigest()
```

---

### 5. HPP Link Creation Fails

**Symptoms:**
- Token generation successful
- But HPP link creation fails
- Error: "Unable to create payment link"

**Diagnosis:**
```bash
tail -f ~/swimtcsp/logs/payments.log | grep "HPP link"
```

**Common Causes:**

#### A. Wrong Account Name
**Check `.env`:**
```bash
BOIPA_ACCOUNT_NAME=ECOMIE7200018387978  # Should match BOIPA credentials
```

#### B. Invalid Amount
**Check:** Amount must be in cents (integer)
```python
# Correct
amount = 11275  # €112.75

# Wrong
amount = 112.75  # Decimal not allowed
```

#### C. Wrong API Endpoint
**Check `.env`:**
```bash
# Sandbox
BOIPA_HPP_LINKS_URL=https://apis.sandbox.globalpay.com/ucp/links

# Production
BOIPA_HPP_LINKS_URL=https://apis.boipagateway.com/ucp/links
```

---

### 6. User Redirects to Wrong Page

**Symptoms:**
- Payment successful
- User redirected to homepage instead of dashboard

**Current Behavior:**
- Success page shows for 2 seconds
- Auto-redirects to homepage

**To Change:**
Edit `boipa/views.py` line 147 and `utils/middleware.py` line 113:
```python
# Current
redirect_url = request.build_absolute_uri(reverse('home'))

# To redirect to dashboard
redirect_url = request.build_absolute_uri(reverse('swimling_dashboard:guardian_dashboard'))
```

---

### 7. Emails Not Sending

**Symptoms:**
- Payment processed
- Order marked paid
- Enrollment created
- But no email sent

**Diagnosis:**
```bash
tail -f ~/swimtcsp/logs/payments.log | grep "Email"
```

**Check:**
1. Email task was called:
   ```python
   # Should see in logs
   "📧 Email sent for order X"
   ```

2. Email settings in production:
   ```python
   # config/production_settings.py
   EMAIL_HOST = config('EMAIL_HOST')
   EMAIL_HOST_USER = config('EMAIL_HOST_USER')
   EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
   ```

3. Celery/task queue running (if using async emails)

---

### 8. Duplicate Enrollments Created

**Symptoms:**
- User pays once
- Multiple enrollments created for same lesson

**Cause:** Webhook called multiple times

**Solution:** Idempotency check in `payment_notification`:
```python
# boipa/views.py lines 289-291
if tx_id and NotificationModel.objects.filter(order=order, txId=tx_id).exists():
    logger.info(f"ℹ️ Duplicate notification ignored for order {order.id}, txId={tx_id}")
    return HttpResponse("Already processed", status=200)
```

---

### 9. Refund Fails

**Symptoms:**
- Try to refund order
- Error returned

**Check:**
1. Order has `txId` set
2. Order is marked `paid=True`
3. Using correct API endpoint:
   ```bash
   BOIPA_TRANSACTIONS_URL=https://apis.boipagateway.com/ucp/transactions
   ```

4. Refund function has access token:
   ```python
   # boipa/payment_functions.py - refund_boipa_transaction()
   ```

---

## 🔍 Debugging Tools

### Check Order Status
```python
from lessons_orders.models import Order
order = Order.objects.get(id=XXX)
print(f"Paid: {order.paid}")
print(f"TxId: {order.txId}")
print(f"Amount: {order.amount}")
```

### Check Enrollment Created
```python
from lessons_bookings.models import LessonEnrollment
enrollments = LessonEnrollment.objects.filter(order__id=XXX)
print(f"Enrollments: {enrollments.count()}")
for e in enrollments:
    print(f"  - {e.swimling.first_name} in {e.lesson.name}")
```

### Check Payment Notification Received
```python
from boipa.models import LessonOrderPaymentNotification
notif = LessonOrderPaymentNotification.objects.filter(order__id=XXX)
print(f"Notifications: {notif.count()}")
for n in notif:
    print(f"  - TxId: {n.txId}, Status: {n.status}")
```

### Test OAuth2 Token Generation
```python
from boipa.payment_functions import get_boipa_access_token
token_data = get_boipa_access_token()
if token_data:
    print(f"✅ Token: {token_data['token'][:50]}...")
    print(f"Expires in: {token_data.get('expires_in')} seconds")
else:
    print("❌ Token generation failed")
```

### Test HPP Link Creation
```python
from boipa.payment_functions import create_hpp_payment_link
from decimal import Decimal

# Mock request (you'll need a real request object)
class MockRequest:
    scheme = 'https'
    def get_host(self): return 'www.tcsp.ie'

link_data = create_hpp_payment_link(MockRequest(), "test_123", Decimal("10.00"))
if link_data:
    print(f"✅ Link: {link_data['url']}")
else:
    print("❌ Link creation failed")
```

---

## 📊 Monitoring Commands

### Watch Payment Logs Live
```bash
tail -f ~/swimtcsp/logs/payments.log
```

### Watch for Errors Only
```bash
tail -f ~/swimtcsp/logs/payments.log | grep -i "error\|fail\|exception"
```

### Check Last 100 Payment Events
```bash
tail -100 ~/swimtcsp/logs/payments.log
```

### Count Successful Payments Today
```bash
grep "✅ Order.*marked paid" ~/swimtcsp/logs/payments.log | grep "$(date +%Y-%m-%d)" | wc -l
```

---

## 🆘 Emergency Contacts

**BOIPA Support:**
- Email: ecommerce@boipa.com
- Phone: 1800 806 670
- Portal: https://portal.boipagateway.com

**Ticket Reference:** BOIPA-6530

**Your Support Resources:**
- Sandbox Credentials: See `SANDBOX_TEST_RESULTS.md`
- Production Credentials: See `BOIPA_NEW_API_DOCUMENTATION.md`
- Deployment Guide: See `PRODUCTION_DEPLOYMENT_CHECKLIST.md`

---

## ✅ Health Check Checklist

Run these checks periodically:

- [ ] Can generate OAuth2 token
- [ ] Can create HPP link
- [ ] Recent payments processing
- [ ] No errors in logs (last hour)
- [ ] Emails being sent
- [ ] BOIPA portal showing recent transactions

---

**Note:** This guide covers the new BOIPA Developer Portal API only. For old API issues, refer to legacy documentation.