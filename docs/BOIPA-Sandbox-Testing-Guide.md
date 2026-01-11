# BOIPA Sandbox Testing Guide

## Overview

This guide explains how to test your TCSP payment integration with BOIPA's sandbox (UAT) environment using real test card numbers and complete end-to-end payment flows.

## What's Different: Automated Tests vs Sandbox Testing

### Automated Integration Tests
✅ **What they do:**
- Run locally or on dev server
- Mock BOIPA token generation
- Simulate webhook POST requests
- Test your webhook processing logic
- Fast, isolated, no external dependencies

❌ **What they DON'T do:**
- Don't connect to BOIPA servers
- Don't use real payment forms
- Don't test actual 3D Secure flows
- Don't require real card numbers

### Manual Sandbox Testing
✅ **What you test:**
- Complete end-to-end flow with BOIPA
- Real BOIPA Hosted Payment Page (HPP)
- Actual 3D Secure v2.1 authentication
- Real webhook callbacks from BOIPA
- Different card scenarios (success, decline, challenge, etc.)

✅ **Why you need it:**
- Verify BOIPA API integration
- Test 3DS challenge flows
- Confirm webhook URL is reachable
- Validate real payment form behavior
- End-to-end confidence before production

## Prerequisites

### 1. BOIPA Sandbox Credentials

**Environment Variables** (update your `.env` file):

```bash
# BOIPA Sandbox Configuration
BOIPA_MERCHANT_ID=100121
BOIPA_PASSWORD=qWGEJQQAkhROSTGpwS5O
BOIPA_TOKEN_URL=https://apiuat.test.boipapaymentgateway.com/token
BOIPA_PAYMENT_URL=https://apiuat.test.boipapaymentgateway.com/payments
HPP_FORM=https://cashierui-apiuat.test.boipapaymentgateway.com/
```

**Note:** These credentials are already in your codebase comments. Verify with BOIPA if they're still current.

### 2. Webhook Setup

BOIPA needs to POST to your webhook URL: `/boipa/payment-notification/`

#### Option A: PythonAnywhere Development Site (Recommended)

Your dev site is already publicly accessible:
```
https://yourusername.pythonanywhere.com/boipa/payment-notification/
```

✅ **Advantages:**
- Already public - no extra setup
- Separate from production
- Can test with real database
- Can monitor Django logs in real-time

**Setup:**
1. Login to PythonAnywhere dev site
2. Ensure BOIPA sandbox credentials in `.env`
3. Reload web app
4. Ready to test!

#### Option B: Local Development with ngrok

If testing locally, use ngrok to expose your dev server:

```bash
# Terminal 1: Start Django dev server
python manage.py runserver

# Terminal 2: Start ngrok tunnel
ngrok http 8000
```

ngrok gives you a public URL like: `https://abc123.ngrok.io`

**Update `.env`:**
```bash
NGROK=https://abc123.ngrok.io
```

Now BOIPA can reach: `https://abc123.ngrok.io/boipa/payment-notification/`

⚠️ **Important:** ngrok URLs expire when you close the tunnel. You'll get a new URL each time.

## BOIPA Test Cards

**IMPORTANT:** You MUST use the official test cards from the BOIPA Developer Portal. These test cards are updated as of January 2026.

Source: https://developer.globalpay.com → Getting Started → Test Cards

### Quick Reference - Official BOIPA Sandbox Test Cards

| Card Type | Card Number | Expiry | CVV | Expected Result |
|-----------|-------------|--------|-----|-----------------|
| **Visa** | 4263970000005262 | 05/39 | 123 | ✅ Successful transaction |
| **Visa** | 4024007134364842 | 05/39 | 123 | ✅ Successful transaction |
| **Mastercard** | 2223000010005780 | 05/39 | 900 | ✅ Successful transaction |
| **Mastercard** | 5425230000004415 | 05/39 | 123 | ✅ Successful transaction |
| **American Express** | 374101000000608 | 05/39 | 1234 | ✅ Successful transaction |
| **Diners Club** | 36256000000725 | 05/39 | 1234 | ✅ Successful transaction |
| **Discover** | 6011000000000087 | 05/39 | 599 | ✅ Successful transaction |
| **JCB** | 3566000000000000 | 05/39 | 599 | ✅ Successful transaction |

**Note:** All test cards use expiry `05/39` in the BOIPA sandbox. Do NOT use random test card numbers - they will be declined.

### Detailed Test Cards

#### ✅ Successful Payment - Visa (Recommended for Quick Testing)

**Primary Visa Card:**
- Card: `4263970000005262`
- CVV: `123`
- Expiry: `05/39`
- **Flow:** Instant approval
- **Best for:** Quick success testing, most commonly used

**Alternative Visa Card:**
- Card: `4024007134364842`
- CVV: `123`
- Expiry: `05/39`

#### ✅ Successful Payment - Mastercard

**Primary Mastercard:**
- Card: `2223000010005780`
- CVV: `900`
- Expiry: `05/39`
- **Flow:** Instant approval

**Alternative Mastercard:**
- Card: `5425230000004415`
- CVV: `123`
- Expiry: `05/39`

#### ✅ Successful Payment - American Express

**American Express:**
- Card: `374101000000608`
- CVV: `1234`
- Expiry: `05/39`
- **Note:** Amex uses 4-digit CVV

#### ✅ Successful Payment - Other Cards

**Diners Club:**
- Card: `36256000000725`
- CVV: `1234`
- Expiry: `05/39`

**Discover:**
- Card: `6011000000000087`
- CVV: `599`
- Expiry: `05/39`

**JCB:**
- Card: `3566000000000000`
- CVV: `599`
- Expiry: `05/39`

#### ⚠️ Testing Declined Payments

For testing declined payments, check the BOIPA Developer Portal for current test cases:
- https://developer.globalpay.com → Getting Started → Test Cases

The test cases may include specific amount-based testing or response code testing.

## Complete Test Workflow

### Test Scenario 1: Successful Swim Order Payment

**Objective:** Verify swim order payment and confirmation

**Steps:**

1. **Login to Development Site**
   ```
   https://yourusername.pythonanywhere.com/
   ```

2. **Create a Test Order**
   - Navigate to public swims
   - Select a swim session
   - Add to cart
   - Proceed to checkout

3. **Payment Page**
   - You'll be redirected to BOIPA Hosted Payment Page
   - **Enter test card:**
     - Card: `4263970000005262`
     - CVV: `123`
     - Expiry: `05/39`
     - Name: Any name
   - Click "Pay"

4. **Expected Flow:**
   - ✅ Payment processes (frictionless, no challenge)
   - ✅ Redirected back to your site
   - ✅ Order confirmation page shown
   - ✅ BOIPA webhook fires to `/boipa/payment-notification/`
   - ✅ Order marked as `paid=True`
   - ✅ SwimOrderPaymentNotification created
   - ✅ Confirmation email sent

5. **Verification:**
   - Check Django admin: `/admin/`
   - Find your order in Swim Orders
   - Verify:
     - `paid` = True ✅
     - `txId` = BOIPA transaction ID ✅
     - Payment notification record exists ✅

### Test Scenario 2: Successful Lesson Order with Enrollment

**Objective:** Verify lesson payment creates enrollment

**Steps:**

1. **Create Test Order**
   - Navigate to lessons
   - Select a lesson (ensure current term exists!)
   - Add to cart
   - Proceed to checkout

2. **Payment**
   - **Use standard test card:**
     - Card: `4263970000005262`
     - CVV: `123`
     - Expiry: `05/39`
   - Click "Pay"

   **Note:** For 3DS challenge testing, check BOIPA Developer Portal for current 3DS test cards.

3. **Expected Flow:**
   - ✅ Payment processed
   - ✅ Redirected to confirmation
   - ✅ Webhook fires
   - ✅ Order marked paid
   - ✅ **LessonEnrollment created** ⭐
   - ✅ Email sent

4. **Verification:**
   - Check Lesson Orders in admin
   - **Most Important:** Check Lesson Enrollments
   - Verify enrollment exists:
     - Swimling: Your test child ✅
     - Lesson: The lesson you booked ✅
     - Term: Current term ✅
     - Order: Links to your paid order ✅

### Test Scenario 3: Failed Payment (Declined Card)

**Objective:** Verify declined payment handling

**Steps:**

1. **Create Test Order**
   - Add any lesson or swim to cart
   - Proceed to checkout

2. **Payment with Declined Card**
   - **Note:** Check BOIPA Developer Portal for current decline test cases.
   - Declined payments may be tested using specific amounts or test cards.
   - See: https://developer.globalpay.com → Getting Started → Test Cases

3. **Expected Flow:**
   - ❌ Payment declined
   - ❌ Error message shown
   - ✅ Webhook still fires (with failure status)
   - ✅ Order remains `paid=False`
   - ❌ NO enrollment created
   - ❌ NO confirmation email sent

4. **Verification:**
   - Order status: `paid=False` ✅
   - Payment notification: `status=DECLINED` ✅
   - Lesson Enrollments: None for this order ✅

### Test Scenario 4: School Order Payment

**Objective:** Verify school lesson payment and enrollment

**Steps:**

1. **Login as School Admin/Coordinator**

2. **Create School Order**
   - Navigate to school bookings
   - Select school lessons
   - Add students
   - Checkout

3. **Payment**
   - Use: `2223000010005780` (Mastercard)
   - CVV: `900`
   - Expiry: `05/39`

4. **Expected Flow:**
   - ✅ Payment succeeds
   - ✅ **ScoEnrollment created** for each student
   - ✅ School orders admin shows paid order

5. **Verification:**
   - School Orders: Paid ✅
   - School Enrollments: Created ✅
   - Each student enrolled ✅

## Monitoring & Debugging

### Check BOIPA Webhook Logs

Your BOIPA webhook logging is already configured. Check logs:

**Local Development:**
```bash
tail -f logs/boipa.log
```

**PythonAnywhere:**
- Go to Files → logs/
- View `boipa.log`
- Real-time updates as webhooks fire

### Django Admin Checks

1. **Payment Notifications**
   - `/admin/boipa/` (various notification models)
   - Check txId, status, errorMessage
   - Verify webhook data captured

2. **Orders**
   - Swim Orders: `/swimsadmin/`
   - Lesson Orders: `/lessonsadmin/`
   - School Orders: `/schoolsadmin/`
   - Check `paid` status, `txId`

3. **Enrollments**
   - Lesson Enrollments: `/lessonsadmin/`
   - School Enrollments: `/schoolsadmin/`
   - Verify created after payment

### Common Issues

#### Issue: Webhook Not Firing

**Symptoms:**
- Payment succeeds on BOIPA
- But order not marked paid
- No payment notification record

**Check:**
1. Is webhook URL publicly accessible?
   - Test: `curl https://yourusername.pythonanywhere.com/boipa/payment-notification/`
   - Should return 405 Method Not Allowed (expected for GET)
2. Check BOIPA logs for webhook errors
3. Verify NGROK tunnel still running (if local)

#### Issue: Enrollment Not Created

**Symptoms:**
- Order marked paid ✅
- But no LessonEnrollment or ScoEnrollment

**Check:**
1. OrderItem has `term` set?
   - Check in Django admin
   - Without term, enrollment fails
2. Check enrollment logs:
   ```bash
   grep "Enrollment" logs/boipa.log
   ```
3. Unique constraint violation?
   - Student may already be enrolled
   - Check existing enrollments

#### Issue: 3DS Challenge Not Appearing

**Symptoms:**
- Using challenge card (4111111111111111)
- But no PIN prompt appears

**Possible Causes:**
1. Card defaults to frictionless in sandbox
2. Try different challenge card
3. Check BOIPA sandbox configuration

#### Issue: All Payments Failing

**Check:**
1. BOIPA credentials correct?
2. Using sandbox URLs (not production)?
3. Merchant ID = `100121`?
4. Token generation succeeding?

## Test Checklist

Use this checklist before deploying to production:

### Swim Orders
- [ ] Create swim order
- [ ] Pay with frictionless card → Success
- [ ] Order marked paid
- [ ] Notification recorded
- [ ] Email received
- [ ] Pay with declined card → Failure
- [ ] Order remains unpaid

### Lesson Orders
- [ ] Create lesson order (ensure term exists!)
- [ ] Pay with challenge card
- [ ] Complete 3DS with PIN 1234
- [ ] Order marked paid
- [ ] **LessonEnrollment created**
- [ ] Enrollment links to order
- [ ] Email received
- [ ] Try duplicate enrollment → Prevented

### School Orders
- [ ] Create school order
- [ ] Multiple students
- [ ] Pay successfully
- [ ] **ScoEnrollment created for each student**
- [ ] School admin can see enrollments

### Edge Cases
- [ ] Cancel payment → Order unpaid
- [ ] Wrong PIN → Authentication fails
- [ ] Duplicate webhook → Idempotent handling
- [ ] Network error → Graceful failure

## Using Test Cards in Automated Tests

The automated tests DON'T actually use these cards (they mock the webhook). But you can reference them for documentation:

```python
from boipa.test_cards import BOIPATestCards

# In test comments/documentation
def test_swim_order_complete_payment_flow(self):
    """
    Simulates successful payment.

    For manual testing, use:
    Card: {BOIPATestCards.VISA_FRICTIONLESS_SUCCESS['number']}
    CVV: {BOIPATestCards.VISA_FRICTIONLESS_SUCCESS['cvv']}
    """
    # ... test code
```

## Production Checklist

Before switching to production BOIPA:

- [ ] Update `.env` with production credentials
- [ ] Change BOIPA URLs to production
- [ ] Update merchant ID to production value
- [ ] Test ONE small real transaction
- [ ] Monitor webhook logs closely
- [ ] Verify enrollment creation
- [ ] Confirm email sending
- [ ] Check payment appears in BOIPA dashboard
- [ ] Verify funds captured

## Quick Test Card Reference

**Copy-paste these for quick testing (Updated January 2026):**

### ✅ Success - Visa (RECOMMENDED)
```
Card: 4263970000005262
CVV: 123
Expiry: 05/39
```

### ✅ Success - Mastercard
```
Card: 2223000010005780
CVV: 900
Expiry: 05/39
```

### ✅ Success - American Express
```
Card: 374101000000608
CVV: 1234
Expiry: 05/39
```

**Note:** For decline testing and 3DS challenge flows, check the BOIPA Developer Portal for current test cases.

## Additional Resources

- **BOIPA Test Cases PDF:** `/docs/Z-TCSP Processes/BOI and Payments Gateway/BOIPA-Test-Cases.pdf`
- **Test Card Reference:** `/boipa/test_cards.py`
- **Automated Tests:**
  - `/swims_orders/tests.py`
  - `/lessons_orders/tests.py`
  - `/schools_orders/tests.py`
- **Integration Summary:** `/docs/boipa-integration-tests-summary.md`

## Support

If you encounter issues:

1. Check logs: `logs/boipa.log`
2. Review BOIPA documentation
3. Contact BOIPA support with:
   - Merchant ID: 100121
   - Transaction ID (txId)
   - Timestamp
   - Error message