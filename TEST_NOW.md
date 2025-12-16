# 🚀 Ready to Test - Quick Reference

**Status:** ✅ All systems ready for manual payment testing
**Date:** December 16, 2025

---

## ✅ What's Running

- **Django Server:** http://localhost:8000 ✅ Running
- **Ngrok Tunnel:** https://261462ec9677.ngrok-free.app ✅ Active
- **Webhook URL:** https://261462ec9677.ngrok-free.app/boipa/payment-notification/
- **Sandbox API:** Connected to `apis.sandbox.globalpay.com`

---

## 🧪 Test Payment Now

### 1. Open Your Browser

Go to: **http://localhost:8000**

### 2. Log In

Use any test user account or create one.

### 3. Add Item to Cart

- Add a **lesson** to your cart (recommended for first test)
- Or add a **swim session**

### 4. Go to Checkout

Click "Checkout" or "Proceed to Payment"

### 5. You'll Be Redirected to BOIPA

The sandbox hosted payment page will open.

### 6. Enter Test Card Details

Use this **successful test card:**

```
Card Number:  4263970000005262
Expiry Date:  12/25 (any future date works)
CVV:          123
Cardholder:   Test User
```

**Billing Address (if asked):**
```
Street:    123 Main Street
City:      Dublin
Postcode:  D02 X285
Country:   IE (Ireland)
```

### 7. Complete 3D Secure

- If prompted for 3D Secure authentication, follow the on-screen test instructions
- In sandbox, you can usually just click "Continue" or "Approve"

### 8. Wait for Redirect

You'll be redirected back to your success page at:
`http://localhost:8000/boipa/payment-response/`

---

## ✅ What to Check After Payment

### In Your Browser:
- ✅ See "Payment Successful" message
- ✅ Order reference displayed
- ✅ Confirmation details shown

### In Terminal - Check Logs:
```bash
tail -50 logs/boipa.log
```

**Look for:**
```
📥 payment_notification view triggered
✅ Order saved: id=..., paid=True
📝 Payment notification record created
📚 Enrollment done for order ...
📧 Email dispatched for order ...
```

### In Django Shell - Check Database:
```bash
python manage.py shell
```

```python
from lessons_orders.models import LessonOrder
from boipa.models import LessonOrderPaymentNotification
from lessons_bookings.models import LessonEnrollment

# Get your latest order
order = LessonOrder.objects.latest('id')
print(f"\n🛒 Order {order.id}:")
print(f"   Paid: {order.paid}")  # Should be True ✅
print(f"   TxId: {order.txId}")  # Should have BOIPA transaction ID

# Check webhook
notification = LessonOrderPaymentNotification.objects.filter(order=order).first()
print(f"\n📥 Webhook:")
print(f"   Received: {'✅ Yes' if notification else '❌ No'}")
if notification:
    print(f"   Status: {notification.status}")
    print(f"   TxId: {notification.txId}")

# Check enrollment
enrollments = LessonEnrollment.objects.filter(order=order)
print(f"\n📚 Enrollments:")
print(f"   Count: {enrollments.count()}")
for enrollment in enrollments:
    print(f"   - {enrollment.swimling.first_name}: {enrollment.lesson}")
```

---

## 🧪 Test Scenarios

### ✅ Test 1: Successful Payment (DO THIS FIRST)
- Card: `4263970000005262`
- Expected: Payment succeeds, order marked paid, enrollment created

### ✅ Test 2: Declined Payment
- Card: `4000120000001154`
- Expected: Payment declined, order stays unpaid, graceful error message

### ✅ Test 3: Different Order Type
- Try a **swim session** order instead of lesson
- Verify same success flow

---

## 🐛 Troubleshooting

### Issue: Webhook Not Received

**Check ngrok:**
```bash
curl http://127.0.0.1:4040/api/tunnels
```

If ngrok stopped, restart it:
```bash
ngrok http 8000
```
Then update `NGROK=` in `.env` with the new URL and restart Django.

### Issue: Django Server Not Running

```bash
lsof -ti:8000 | xargs kill -9
python manage.py runserver
```

### Issue: Payment Link Creation Fails

Check logs:
```bash
tail -20 logs/boipa.log
```

Look for authentication errors or API errors.

### Issue: 3D Secure Fails

This is expected in sandbox - just follow the test prompts. Usually you can click "Continue" or "Submit" without real authentication.

---

## 💳 Test Card Reference

**Successful:**
- `4263970000005262` - Visa (3D Secure)
- `5425230000004415` - Mastercard

**Declined:**
- `4000120000001154` - Declined by bank
- `4000160000004147` - Lost/stolen card

See full list: `docs/BOIPA_TEST_CARDS.md`

---

## 📝 Document Your Results

After testing, update: **`docs/SANDBOX_TEST_RESULTS.md`**

Add your results for:
- Test 1: Successful payment ✅ / ❌
- Webhook received ✅ / ❌
- Enrollment created ✅ / ❌
- Email sent ✅ / ❌

---

## 🚀 After All Tests Pass

1. **Switch to production credentials** in `.env`
2. **Update production settings** in `config/production_settings.py`
3. **Deploy to PythonAnywhere**
4. **Test first real transaction** (small amount)
5. **Monitor closely** for 24-48 hours

---

## 📞 Quick Help

**Check Server Status:**
```bash
curl http://127.0.0.1:8000 && echo "✅ Django running" || echo "❌ Django not running"
```

**Check Ngrok Status:**
```bash
curl -s http://127.0.0.1:4040/api/tunnels | python -c "import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])" 2>/dev/null || echo "❌ Ngrok not running"
```

**View Live Logs:**
```bash
tail -f logs/boipa.log
```

**Stop Django:**
```bash
lsof -ti:8000 | xargs kill -9
```

---

## ✨ Current Status

**Environment:** Sandbox ✅
**API Integration:** Working ✅
**Credentials:** Valid ✅
**Server:** Running ✅
**Ngrok:** Active ✅
**Webhooks:** Configured ✅

**Next Step:** Open http://localhost:8000 and complete a test checkout! 🎉

---

**For detailed instructions, see:** `SANDBOX_TEST_INSTRUCTIONS.md`
**For API reference, see:** `docs/BOIPA_NEW_API_DOCUMENTATION.md`