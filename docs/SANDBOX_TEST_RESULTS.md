# Sandbox Test Results

**Date:** December 16, 2025
**Tester:** Morgan McKnight
**Environment:** Sandbox (apis.sandbox.globalpay.com)
**Ticket Reference:** BOIPA-6530

---

## ✅ Sandbox Credentials Received

**From:** Stephen Judge (BOIPA Support)
**Date:** December 16, 2025, 3:15 PM

```
Client ID: EVOIE0CHY0745
Merchant ID: MER_19ba994a76ee403c96e9f458c5f664b5
App ID: C1vHe0PqBzH4ukGANlHW5xAG1jeNpgFu
App Key: QSptsGy9TgzTf9Nf
Account Name: ECOMIE7200018387978
Account ID: TRA_ef38c091212340a5b4731856b71038b2
```

---

## 🧪 Automated Tests - ✅ ALL PASSED

### Test 1: OAuth2 Access Token Generation
- **Status:** ✅ PASS
- **Result:** Token generated successfully
- **Token Type:** Bearer
- **API Endpoint:** `https://apis.sandbox.globalpay.com/ucp/accesstoken`
- **Notes:** OAuth2 client credentials flow with SHA512 signing working correctly

### Test 2: HPP Link Creation
- **Status:** ✅ PASS
- **Link ID:** `LNK_FQ9joh7FZnYlv6OJy8JXExGLyJGcNy`
- **Payment URL:** https://apis.sandbox.globalpay.com/ucp/hpp/redirect/17325907-4853-49f3-b6c9-269c090edead
- **Link Status:** ACTIVE
- **Test Amount:** €25.50
- **Order Reference:** `test_sandbox_1765902008`
- **Notes:** HPP link created successfully via API

**Test Script Output:**
```
🎉 All tests passed! Sandbox integration is working.
```

---

## ✅ FINAL WORKING SOLUTION - Local Testing (Orders 344, 345, 346)

### Successful Test Transactions (Local with ngrok):
- **Order 344:** ✅ COMPLETE - Paid, enrolled, email sent
- **Order 345:** ✅ COMPLETE - Paid, enrolled, email sent
- **Order 346:** ✅ COMPLETE - Paid, enrolled, auto-redirect working

### Key Issues Resolved (Local):
1. **CSRF Protection:** Added `@csrf_exempt` to payment endpoints
2. **JSON Parsing:** New API sends JSON, not form-encoded data
3. **Field Mapping:** Mapped `id` → `txId`, `reference` → `merchantTxId`, `status: CAPTURED` → success
4. **User Redirect:** Created standalone HTML with auto-redirect to handle BOIPA's domain display

### Final Working Flow (Local):
1. User completes payment on BOIPA HPP
2. BOIPA POSTs JSON data to `return_url` (payment_response)
3. Backend processes payment (marks paid, creates enrollment, sends email)
4. Returns simple HTML page with 2-second auto-redirect
5. User redirected back to merchant site

---

## ✅ DEV SERVER TESTING (PythonAnywhere) - December 16, 2025

### Critical Issue Discovered: SessionInterrupted Error

**Problem:**
- Local testing with ngrok worked perfectly
- Dev server (PythonAnywhere) showed blank page after payment
- Logs showed `SessionInterrupted` exception
- Payment was processing successfully, but response couldn't be rendered

**Root Cause:**
- **Local:** User's browser maintains session throughout BOIPA redirect
- **PythonAnywhere:** BOIPA makes server-to-server POST without session cookie
- Django's SessionMiddleware tried to save non-existent session and raised exception

**Solution Implemented:**
Created `PaymentGatewaySessionMiddleware` in `utils/middleware.py`:
- Catches `SessionInterrupted` exceptions on BOIPA callback endpoints
- Extracts order ID from payment data
- Returns standalone HTML success page with auto-redirect
- Placed after `SessionMiddleware` in middleware stack

### Missing Configuration Issue

**Problem:**
- BOIPA wasn't calling back to payment_response endpoint at all
- No logs showing payment response being received

**Root Cause:**
- `NGROK` environment variable not set in dev `.env`
- Code was using default value: `http://localhost:4040`
- BOIPA was trying to call localhost instead of PythonAnywhere URL

**Solution:**
Added to dev `.env`:
```bash
NGROK=https://dev-morganmck.eu.pythonanywhere.com
```

### Dev Server Test Results:

**Environment:** dev-morganmck.eu.pythonanywhere.com
**Date:** December 16, 2025

✅ **All tests passing:**
- OAuth2 token generation working
- HPP link creation successful
- Payment processing complete
- Orders marked paid
- Enrollments created
- Emails sent
- Success page displays correctly
- Auto-redirect to home page working (2 seconds)

**Test Orders:**
- Multiple successful test payments completed
- Session error handling working correctly
- User experience smooth

---

## 📋 Manual Payment Flow Tests

### Test 1: Successful Lesson Order Payment
- **Date:** [PENDING - To be completed]
- **Order ID:** [TBD]
- **Amount:** €XX.XX
- **Card:** 4263970000005262
- **Result:** ⏳ PENDING
- **Webhook Received:** ⏳ PENDING
- **Order Marked Paid:** ⏳ PENDING
- **Enrollment Created:** ⏳ PENDING
- **Email Sent:** ⏳ PENDING
- **Notes:** Awaiting manual testing through full checkout flow

### Test 2: Declined Payment
- **Date:** [PENDING]
- **Card:** 4000120000001154
- **Result:** ⏳ PENDING
- **Order Stayed Unpaid:** ⏳ PENDING
- **Notes:** [To be completed]

### Test 3: Swim Order Payment
- **Date:** [PENDING]
- **Result:** ⏳ PENDING
- **Notes:** [To be completed]

### Test 4: School Order Payment
- **Date:** [PENDING]
- **Result:** ⏳ PENDING
- **Notes:** [To be completed]

### Test 5: Webhook Idempotency
- **Date:** [PENDING]
- **Test Method:** [TBD]
- **Result:** ⏳ PENDING
- **Notes:** [To be completed]

---

## 🔍 Technical Verification

### API Integration
- ✅ OAuth2 authentication working
- ✅ Access token generation successful
- ✅ HPP link creation via API successful
- ✅ Correct sandbox URLs configured
- ✅ All credentials valid

### Code Implementation
- ✅ `boipa/payment_functions.py` - Updated for new API
- ✅ `boipa/views.py` - Payment initiation updated
- ✅ Webhook handler ready (`payment_notification()`)
- ⏳ Refund functionality (pending testing)

### Configuration
- ✅ `.env` updated with sandbox credentials
- ✅ `config/local_settings.py` configured
- ⏳ Production settings files (pending update)

---

## 🐛 Issues Found

**None so far** - Automated tests passed on first attempt.

---

## 📝 Next Steps

1. ⏳ **Set up ngrok tunnel** for webhook testing
   ```bash
   ngrok http 8000
   ```

2. ⏳ **Update `.env`** with current ngrok URL

3. ⏳ **Test complete payment flow:**
   - Start Django server
   - Complete checkout with test card
   - Verify webhook delivery
   - Check database updates
   - Confirm enrollment creation
   - Verify email sending

4. ⏳ **Test declined payment scenario**

5. ⏳ **Test all three order types** (lessons, swims, schools)

6. ⏳ **Document all test results** in this file

7. ⏳ **Switch to production credentials** (after all tests pass)

8. ⏳ **Deploy to PythonAnywhere**

---

## 🎯 Production Readiness Assessment

### Checklist

**Automated Tests:**
- [x] Access token generation
- [x] HPP link creation

**Manual Tests:**
- [ ] Successful payment flow (lessons)
- [ ] Successful payment flow (swims)
- [ ] Successful payment flow (schools)
- [ ] Declined payment handling
- [ ] Webhook delivery and processing
- [ ] Order marked paid correctly
- [ ] Enrollments created correctly
- [ ] Email notifications sent
- [ ] Error handling

**Code Quality:**
- [x] New API functions implemented
- [x] Old API functions deprecated
- [x] Logging added
- [x] Error handling present
- [ ] Refund functionality tested

**Documentation:**
- [x] API documentation complete
- [x] Migration guide created
- [x] Test cards documented
- [x] Testing guide created
- [ ] Test results documented (in progress)

**Deployment:**
- [ ] Production settings updated
- [ ] PythonAnywhere environment variables configured
- [ ] Code deployed
- [ ] First production transaction tested

---

## 📊 Overall Status

**Current Status:** ✅ **AUTOMATED TESTS PASSED**

**Next Milestone:** Complete manual payment flow testing

**Expected Production Deployment:** [TBD - after manual tests pass]

---

## 📞 Support & Resources

**BOIPA Support:**
- Email: ecommerce@boipa.com
- Phone: 1800 806 670
- Ticket: BOIPA-6530
- Contact: Stephen Judge

**Documentation:**
- API Docs: `docs/BOIPA_NEW_API_DOCUMENTATION.md`
- Migration Plan: `docs/PAYMENT_MIGRATION.md`
- Testing Guide: `docs/SANDBOX_TESTING_GUIDE.md`
- Test Cards: `docs/BOIPA_TEST_CARDS.md`
- Next Steps: `SANDBOX_TEST_INSTRUCTIONS.md`

**Test Resources:**
- Test Script: `test_boipa_sandbox.py`
- Test Cards: See `docs/BOIPA_TEST_CARDS.md`
- Sample HPP Link: https://apis.sandbox.globalpay.com/ucp/hpp/redirect/17325907-4853-49f3-b6c9-269c090edead

---

**Last Updated:** December 16, 2025, 4:20 PM
**Status:** Ready for manual testing