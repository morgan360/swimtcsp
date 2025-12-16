# BOIPA Backend Migration Plan

## Overview
This document tracks the migration from the OLD BOIPA API to the NEW BOIPA Developer Portal API.

**IMPORTANT:** This is NOT a provider change - BOIPA is updating their backend/API system.

**Status:** Implementation Phase - Core Payment Functions Complete
**Last Updated:** 2025-12-11
**Target:** New BOIPA Developer Portal API (https://developer.boipagateway.com)

---

## Current BOIPA Integration Analysis

### Architecture Overview
The current payment system integrates BOIPA across three order types:
- **Lesson Orders** (`lessons_orders/`)
- **Swim Orders** (`swims_orders/`)
- **School Orders** (`schools_orders/`)

### Key Integration Points

#### 1. BOIPA App Structure (`/boipa/`)
- **Models** (`models.py`):
  - `SwimOrderPaymentNotification`
  - `LessonOrderPaymentNotification`
  - `SchoolOrderPaymentNotification`
  - `Refund`

- **Views** (`views.py`):
  - `initiate_boipa_payment_session()` - Creates payment session token
  - `payment_notification()` - Webhook handler (POST/GET)
  - `payment_response()` - User redirect after payment
  - `refund_order_view()` - Admin refund processing

- **Payment Functions** (`payment_functions.py`):
  - `get_boipa_session_token()` - Generates session token for HPP

- **Utils** (`utils.py`):
  - `verify_boipa_transaction()` - Transaction verification
  - `refund_boipa_transaction()` - Refund API call

#### 2. Payment Flow
```
Cart → Create Order → Initiate BOIPA Session → Redirect to HPP →
Payment → Webhook Notification → Mark Paid → Create Enrollment → Send Email
```

**Example (Lessons):**
1. User checkout: `lessons_orders/views.py:payment_process()`
2. Order created with `order_ref = f"lessons_{order.id}"`
3. Redirect to: `boipa:initiate_payment_session`
4. BOIPA HPP (Hosted Payment Page) loads
5. Payment completed → BOIPA webhook hits `boipa:payment_notification`
6. Order marked `paid=True`, `txId` stored
7. `handle_lessons_enrollment()` creates `LessonEnrollment` records
8. Confirmation email sent via `send_lesson_order_email()`

#### 3. Order Models Dependencies
Each order model has:
- `paid` (Boolean) - Payment status
- `txId` (CharField) - Payment gateway transaction ID
- `amount` (Decimal) - Total order amount
- `boipa_reconciled` (Boolean) - Financial reconciliation flag

#### 4. Settings Configuration
**Current OLD BOIPA Settings:**
- `BOIPA_MERCHANT_ID` - Merchant identifier
- `BOIPA_PASSWORD` - API password (used in request body)
- `BOIPA_TOKEN_URL` - Token generation endpoint
  - Example (UAT): `https://apiuat.test.boipapaymentgateway.com/token`
- `BOIPA_PAYMENT_URL` - Payment processing endpoint
  - Example (UAT): `https://apiuat.test.boipapaymentgateway.com/payments`
- `HPP_FORM` - Hosted Payment Page URL

**Location:** Configured in `/config/production_settings.py` and `/config/development_settings.py`
**Source:** Environment variables (`.env` file)

---

## New BOIPA Developer Portal - Key Findings

### Documentation Structure
**Portal URL:** https://developer.boipagateway.com

The new portal organizes documentation into these sections:

1. **Getting Started**
   - Overview, registration, token creation
   - Build integration, go live process
   - "New to Payments" section (intro, glossary)

2. **Integration Options**
   - **Plugins**: Adobe Commerce, OpenCart, PrestaShop, WooCommerce
   - **Server-Side SDKs**: Java, PHP, .NET
   - **Client-Side Libraries**: JavaScript, Android, iOS
   - **Direct REST API Access**

3. **Payments**
   - Online payments (HPP, Hosted Fields, Drop-In UI, Direct API)
   - Recurring payments
   - Tokenization (card storage, payers)
   - Payment methods (Apple Pay, Google Pay)
   - Manage payments (capture, refund, reverse, verify)

4. **Risk Management**
   - 3D Secure & SCA (authentication, exemptions)
   - Fraud management (filters, AVS, decision manager)

5. **Operations & Reporting**
   - File processing, real-time reporting

6. **API References**
   - Access tokens, accounts, actions, authentications
   - Payers, stored payment methods, transactions
   - Transfers, verifications

7. **Resources**
   - Test cards, API responses, country codes, currency codes

### Key Changes from Old API

#### Authentication
**OLD:** `merchantId` + `password` in request body
**NEW:** Access token-based authentication (OAuth-style)
- Must register and create an app
- Generate access tokens via API
- Tokens used for all API requests

#### Integration Approaches
The new system offers three tiers:
- **No-Code**: Pre-built plugins (WooCommerce, Magento, etc.)
- **Low-Code**: SDKs for faster implementation
- **High-Code**: Direct REST API for maximum control

#### Hosted Payment Page (HPP)
Still available but may have different parameters/flow in new API

---

## Migration Strategy

### Phase 1: Access New BOIPA Portal ✅ COMPLETE
- [x] Located developer portal: https://developer.boipagateway.com
- [x] Received production credentials (App ID, App Key, Merchant ID, etc.)
- [x] Accessed portal with production account
- [x] Review complete API documentation
- [x] Compare old vs new API endpoints

### Phase 2: Analyze API Differences ✅ COMPLETE
- [x] Document authentication changes (password → access token)
- [x] Map old endpoints to new endpoints
- [x] Identify breaking changes in request/response formats
- [x] Review webhook/notification changes (appears similar)
- [ ] Check refund API differences (pending)
- [x] Verify HPP parameter changes

### Phase 3: Update Authentication ✅ COMPLETE
- [x] Update `get_boipa_session_token()` for new auth flow
- [x] Add access token generation/refresh logic
- [x] Store tokens securely (environment variables)
- [x] Update settings for new API URLs

### Phase 4: Update Payment Functions ✅ MOSTLY COMPLETE
- [x] Modify `initiate_boipa_payment_session()` for new API
- [ ] Update payment notification webhook handler (may work as-is)
- [ ] Adjust response parsing for new format (testing needed)
- [ ] Update refund functions

### Phase 5: Test in Sandbox
- [ ] Test lesson order payment flow
- [ ] Test swim order payment flow
- [ ] Test school order payment flow
- [ ] Test refund processing
- [ ] Test webhook delivery and idempotency
- [ ] Test error handling

### Phase 6: Deploy to Production
- [ ] Update production settings/credentials
- [ ] Deploy code changes
- [ ] Monitor first transactions closely
- [ ] Keep old code available for rollback

### Phase 7: Post-Migration
- [ ] Monitor transaction success rates
- [ ] Update financial reconciliation if needed
- [ ] Archive old API credentials
- [ ] Document new integration

---

## Code Changes Required

### Files to Modify
- [ ] `lessons_orders/views.py` - Update payment_process()
- [ ] `swims_orders/views.py` - Update payment_process()
- [ ] `schools_orders/views.py` - Update payment_process()
- [ ] `lessons_orders/models.py` - Add generic payment fields
- [ ] `swims_orders/models.py` - Add generic payment fields
- [ ] `schools_orders/models.py` - Add generic payment fields
- [ ] `config/base_settings.py` - Add new provider settings
- [ ] `core/urls.py` - Add new payment webhook routes

### New Files to Create
- [ ] `/payments/` app
- [ ] `/payments/providers/` directory
- [ ] Migration files for new payment models

---

## Testing Checklist

### Payment Flow Tests
- [ ] Successful payment (lessons)
- [ ] Successful payment (swims)
- [ ] Successful payment (schools)
- [ ] Failed payment handling
- [ ] Payment cancellation
- [ ] Duplicate webhook handling (idempotency)

### Refund Tests
- [ ] Full refund
- [ ] Partial refund
- [ ] Refund of unpaid order (should fail)

### Edge Cases
- [ ] Network timeout during payment
- [ ] Webhook received before user redirect
- [ ] Multiple webhooks for same transaction
- [ ] Invalid webhook signature

---

## Migration Notes & Decisions

### Session 1 (2025-12-05) - Initial Analysis
- Analyzed current BOIPA integration
- Identified key integration points
- Created migration planning document

### Session 2 (2025-12-05) - New API Research
- Scraped new BOIPA Developer Portal structure
- Identified major change: password auth → access token auth
- Documented available integration options (HPP, SDK, REST API)
- **BLOCKER IDENTIFIED:** Full API documentation requires authenticated portal access

### Session 3 (2025-12-11) - Production Credentials & Implementation
- **BLOCKER RESOLVED:** Received production credentials via email from BOIPA
- Created `/docs/communications/` folder structure for archiving BOIPA emails
- Extracted credentials from 4 PDF emails:
  - Production Merchant ID: `IE7200018387978`
  - Client ID: `EVOIE0CHY0745`
  - Account Name: `ECOMIE7200018387978`
  - App ID: `3rVzj4c9YTwOsBwU9d6wWfM6G2XfV2Dm`
  - App Key: `TVo8VVsSu4JWb49s` (reconstructed from 2 security emails)
- Accessed BOIPA Developer Portal API documentation
- Created comprehensive API documentation in `/docs/BOIPA_NEW_API_DOCUMENTATION.md` (624 lines)
- Updated `.env` with all new production credentials and API endpoints
- Updated `config/local_settings.py` with new BOIPA configuration
- **Completely rewrote** `/boipa/payment_functions.py`:
  - Implemented `get_boipa_access_token()` - OAuth2 token generation using SHA512 signing
  - Implemented `create_hpp_payment_link()` - HPP link creation via new API
  - Preserved old `get_boipa_session_token_OLD()` with deprecation warning
- **Updated** `/boipa/views.py`:
  - Modified `initiate_boipa_payment_session()` to use new `create_hpp_payment_link()`
  - Removed old iframe mode (not supported in new API)
  - Added payer information extraction from authenticated user
  - Simplified flow: create HPP link → redirect to BOIPA hosted page

**Key Technical Decisions:**
- Using OAuth2 Client Credentials flow with SHA512 HMAC signing
- Access tokens expire after 3600 seconds (1 hour)
- HPP link creation now done via API (POST to `/ucp/links`) instead of manual URL construction
- Preserved backward compatibility by keeping old settings with "DEPRECATED" defaults
- Payment webhook handler (`payment_notification()`) should work with minimal changes (webhook format similar)

**Files Modified:**
1. `.env` - Added new production credentials
2. `config/local_settings.py` - New BOIPA settings configuration
3. `boipa/payment_functions.py` - Complete rewrite for new API
4. `boipa/views.py` - Updated initiate payment view

**Files Created:**
1. `/docs/BOIPA_NEW_API_DOCUMENTATION.md` - Complete API reference
2. `/docs/communications/` - Email archive structure

### Recommended Next Steps

**BEFORE TESTING WITH PRODUCTION CREDENTIALS:**

1. **Create Sandbox Test App** (RECOMMENDED):
   - Register/login at https://developer.boipagateway.com
   - Create a new "test app" for sandbox environment
   - Generate sandbox App ID and App Key
   - Add sandbox credentials to `.env` (or separate `.env.sandbox` file)
   - Test complete payment flow in sandbox first
   - Use test cards from BOIPA documentation

2. **After Sandbox Testing Succeeds:**
   - Verify webhook notification format matches expectations
   - Update refund functions in `boipa/utils.py` for new API
   - Update production settings files (`config/production_settings.py`, `config/development_settings.py`)
   - Deploy to PythonAnywhere dev environment
   - Monitor logs for any API errors
   - Perform end-to-end testing with all three order types (lessons, swims, schools)

**ALTERNATIVE (NOT RECOMMENDED):**
- Test directly with production credentials using small amount (€0.01-€1.00)
- Risk: Real money transactions, potential failed payments in production database

---

## Questions & Blockers

### ✅ Resolved
1. **BLOCKER:** Cannot access full API docs without portal login
   **Status:** ✅ RESOLVED - Production credentials received, API docs accessed and documented

2. **Q:** Do we have new BOIPA credentials (app ID, API keys)?
   **A:** ✅ YES - Received via email Dec 8, 2025. All credentials extracted and stored in `.env`

### Remaining Questions
3. **Q:** Has BOIPA provided migration documentation or guides?
   **A:** Received production credentials and portal access. Using official API documentation from developer portal.

4. **Q:** What is the deadline for this migration?
   **A:** ⚠️ UNKNOWN - Old IPG/Turnkey system marked as "end-of-life" but exact shutdown date not specified. URGENT: Need to confirm deadline with BOIPA.

5. **Q:** Is there a testing/staging environment available?
   **A:** ✅ YES - BOIPA provides a **free Sandbox test environment**. Requires registration at developer portal to create test app credentials (separate from production). Can test integration before going live.

6. **Q:** What is the cutover strategy? (Big bang vs gradual)
   **A:** Recommend: Deploy to local dev → Test thoroughly → Deploy to staging → Production cutover with monitoring. Need business approval.

7. **Q:** What happens to in-flight transactions during cutover?
   **A:** ⚠️ TO BE DETERMINED - Need strategy for orders created but not yet paid during deployment window.

---

## Resources

### New BOIPA Documentation
- **Developer Portal:** https://developer.boipagateway.com
- **Plugin Docs:** https://developer.boipagateway.com/docs/integration-options/plugins
- **API Reference:** (Requires login)
- **Current Implementation:** `/boipa/` directory

### Current BOIPA URLs (from code)
Check `config/base_settings.py` for:
- `BOIPA_TOKEN_URL` - Current token endpoint
- `BOIPA_PAYMENT_URL` - Current payment endpoint
- `HPP_FORM` - Current Hosted Payment Page URL

### Helpful Sections to Review (after login)
- "Getting Started" → "Create an Access Token"
- "Payments" → "Online Payments" → "Hosted Payment Page"
- "API References" → "Transactions"
- "Resources" → "Test Cards" (for sandbox testing)

---

## Contact & Support
- **Primary Developer:** [Your name]
- **Questions:** Add to this document or create GitHub issue