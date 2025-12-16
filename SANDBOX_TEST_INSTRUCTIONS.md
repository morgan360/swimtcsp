# ✅ SANDBOX TESTS PASSED - Next Steps

**Date:** December 16, 2025
**Status:** Automated tests ✅ PASSED - Ready for manual payment flow testing

---

## 🎉 What Just Worked

✅ **Access Token Generation** - OAuth2 authentication working
✅ **HPP Link Creation** - Payment links being created successfully
✅ **Sandbox Credentials** - All credentials from Stephen Judge are valid

**Test Results:**
- Merchant ID: `MER_19ba994a76ee403c96e9f458c5f664b5`
- Account: `ECOMIE7200018387978`
- API Base: `https://apis.sandbox.globalpay.com`
- Sample HPP Link: https://apis.sandbox.globalpay.com/ucp/hpp/redirect/17325907-4853-49f3-b6c9-269c090edead

---

## 📝 Next: Test Complete Payment Flow

To test the full payment flow with webhooks, you need:

### Step 1: Start ngrok Tunnel (for webhooks)

Open a **new terminal window** and run:

```bash
ngrok http 8000
```

This will output something like:
```
Forwarding  https://abc123def456.ngrok-free.app -> http://localhost:8000
```

Copy the HTTPS URL (e.g., `https://abc123def456.ngrok-free.app`)

### Step 2: Update .env with ngrok URL

Update the `NGROK` variable in your `.env` file:

```bash
NGROK=https://abc123def456.ngrok-free.app
```

**Note:** Your current ngrok URL in `.env` is `https://9d8fd7d86f31.ngrok-free.app` - this may be expired. Get the new one from the ngrok terminal.

### Step 3: Restart Django Server

```bash
# Stop current server (if running): Ctrl+C
# Start fresh server:
python manage.py runserver
```

This ensures Django loads the new ngrok URL.

### Step 4: Test Payment Through Your App

Open browser and test a real checkout flow:

1. **Go to:** http://localhost:8000
2. **Log in** as a test user
3. **Add a lesson to cart** (or swim session)
4. **Proceed to checkout**
5. **You'll be redirected to BOIPA sandbox payment page**
6. **Use test card:**
   - Card Number: `4263970000005262`
   - Expiry: `12/25` (any future date)
   - CVV: `123`
   - Name: `Test User`
7. **Complete 3D Secure** if prompted (follow on-screen test instructions)
8. **You'll be redirected back** to your success page

### Step 5: Verify Everything Worked

#### Check the browser:
- ✅ Redirected to payment success page
- ✅ Order reference displayed

#### Check the database:
```bash
python manage.py shell
```

```python
from lessons_orders.models import LessonOrder
from boipa.models import LessonOrderPaymentNotification

# Find your test order
order = LessonOrder.objects.latest('id')
print(f"Order {order.id}:")
print(f"  Paid: {order.paid}")  # Should be True
print(f"  TxId: {order.txId}")   # Should have BOIPA transaction ID

# Check webhook notification
notification = LessonOrderPaymentNotification.objects.filter(order=order).first()
if notification:
    print(f"  Webhook received: ✅")
    print(f"  Status: {notification.status}")
else:
    print(f"  Webhook received: ❌")

# Check enrollment
from lessons_bookings.models import LessonEnrollment
enrollments = LessonEnrollment.objects.filter(order=order)
print(f"  Enrollments created: {enrollments.count()}")
```

#### Check logs:
```bash
tail -50 logs/boipa.log
```

Look for:
- `📥 payment_notification view triggered`
- `✅ Order saved: id=..., paid=True`
- `📝 Payment notification record created`
- `📚 Enrollment done for order ...`
- `📧 Email dispatched for order ...`

---

## 🧪 Additional Test Scenarios

### Test 2: Declined Payment

1. Go through checkout again
2. Use declined card: `4000120000001154`
3. **Expected result:**
   - Payment fails on BOIPA page
   - Redirected to failure page
   - Order stays `paid=False`
   - No enrollment created

### Test 3: Swim Order Payment

Test with a swim session order instead of a lesson order.

### Test 4: Multiple Items in Cart

Add multiple lessons/swims and test checkout with larger order.

---

## 📊 What to Document

Create a file `/docs/SANDBOX_TEST_RESULTS.md` with:

```markdown
# Sandbox Test Results

**Date:** December 16, 2025
**Tester:** Morgan
**Environment:** Sandbox

## Automated Tests
✅ Access Token Generation - PASS
✅ HPP Link Creation - PASS

## Manual Payment Flow Tests

### Test 1: Successful Lesson Order Payment
- **Date:** [timestamp]
- **Order ID:** [id]
- **Amount:** €XX.XX
- **Card:** 4263970000005262
- **Result:** ✅ SUCCESS / ❌ FAIL
- **Webhook Received:** ✅ YES / ❌ NO
- **Order Marked Paid:** ✅ YES / ❌ NO
- **Enrollment Created:** ✅ YES / ❌ NO
- **Email Sent:** ✅ YES / ❌ NO
- **Notes:** [any observations]

### Test 2: Declined Payment
- **Card:** 4000120000001154
- **Result:** ✅ DECLINED AS EXPECTED / ❌ UNEXPECTED
- **Order Stayed Unpaid:** ✅ YES / ❌ NO
- **Notes:** [any observations]

### Test 3: Webhook Idempotency
- **Test:** [How you tested duplicate webhooks]
- **Result:** ✅ PASS / ❌ FAIL
- **Notes:** [observations]

## Issues Found
- [ ] None
- [ ] Issue 1: [description]
  - Resolution: [how fixed]

## Production Readiness Assessment
- [ ] All automated tests pass
- [ ] Successful payment flow works
- [ ] Declined payment handled correctly
- [ ] Webhooks received and processed
- [ ] Enrollments created correctly
- [ ] Emails sent correctly
- [ ] Error handling works
- [ ] Ready to deploy to production

**Overall Status:** ✅ READY / ⚠️ ISSUES FOUND / ❌ NOT READY

**Recommendation:** [Deploy to production / Fix issues first / Need more testing]
```

---

## 🚀 After All Tests Pass

### Switch to Production Credentials

1. **Edit `.env`:**
   - Comment out sandbox credentials
   - Uncomment production credentials

```bash
# 🧪 Sandbox Test Environment - COMMENT OUT AFTER TESTING
# BOIPA_MERCHANT_ID=MER_19ba994a76ee403c96e9f458c5f664b5
# BOIPA_APP_ID=C1vHe0PqBzH4ukGANlHW5xAG1jeNpgFu
# BOIPA_APP_KEY=QSptsGy9TgzTf9Nf
# BOIPA_API_BASE_URL=https://apis.sandbox.globalpay.com

# 🔴 PRODUCTION (LIVE) - UNCOMMENT FOR PRODUCTION
BOIPA_MERCHANT_ID=IE7200018387978
BOIPA_CLIENT_ID=EVOIE0CHY0745
BOIPA_ACCOUNT_NAME=ECOMIE7200018387978
BOIPA_APP_ID=3rVzj4c9YTwOsBwU9d6wWfM6G2XfV2Dm
BOIPA_APP_KEY=TVo8VVsSu4JWb49s
BOIPA_API_BASE_URL=https://apis.boipagateway.com
BOIPA_ACCESS_TOKEN_URL=https://apis.boipagateway.com/ucp/accesstoken
BOIPA_HPP_LINKS_URL=https://apis.boipagateway.com/ucp/links
BOIPA_TRANSACTIONS_URL=https://apis.boipagateway.com/ucp/transactions
```

2. **Update production settings files:**
   - `config/production_settings.py`
   - `config/development_settings.py`

3. **Deploy to PythonAnywhere:**
```bash
# Commit all changes
git add .
git commit -m "BOIPA migration complete - tested in sandbox

- OAuth2 authentication working
- HPP link creation verified
- Webhook processing confirmed
- All payment flows tested successfully
- Ready for production deployment"

git push origin main

# Deploy
./deploy-to-dev.sh
```

4. **Test first production transaction:**
   - Use small amount (€1-5)
   - Real credit card
   - Monitor logs closely
   - Verify success before enabling for customers

---

## ⚠️ Important Notes

1. **ngrok URL changes** every time you restart ngrok (free plan)
   - Remember to update `.env` each time
   - Or use a paid ngrok plan for permanent URL

2. **Sandbox vs Production URLs:**
   - Sandbox: `https://apis.sandbox.globalpay.com`
   - Production: `https://apis.boipagateway.com`

3. **Test Cards** only work in sandbox environment

4. **Production webhooks** will go to `https://www.tcsp.ie` (no ngrok needed)

---

## 📞 Support

**BOIPA Support:**
- Email: ecommerce@boipa.com
- Ticket: BOIPA-6530
- Contact: Stephen Judge
- Developer Portal: https://developer.boipagateway.com

**Your Test Results:**
- All automated tests: ✅ PASSED
- HPP Link Example: https://apis.sandbox.globalpay.com/ucp/hpp/redirect/17325907-4853-49f3-b6c9-269c090edead
- Test Cards: See `docs/BOIPA_TEST_CARDS.md`

---

**Ready to proceed with manual testing!** 🚀

Follow Steps 1-5 above to test the complete payment flow.