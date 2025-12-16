# Email to BOIPA Support - Sandbox Credentials Request

**Date:** December 11, 2025
**To:** BOIPA Support (support@boipa.com or your contact at BOIPA)
**Subject:** Request for Sandbox Environment API Credentials - Templeogue College Swim Pool

---

## Email Draft

```
Subject: Request for Sandbox Environment API Credentials - Templeogue College Swim Pool

Dear BOIPA Support Team,

I am writing to request sandbox environment credentials for testing our payment integration before deploying to production.

**Account Details:**
- Merchant Name: Templeogue College Swim Pool
- Merchant ID (Production): IE7200018387978
- Client ID: EVOIE0CHY0745
- Account Name: ECOMIE7200018387978
- Portal Username: TempSwimPool

**Production Credentials Received:**
We have successfully received our production API credentials (App ID and App Key) and can access the Reporting Portal at https://portal.boipagateway.com.

**Request:**
We are now ready to begin integration testing and require sandbox environment credentials to test our payment flow before going live. Specifically, we need:

1. **Sandbox Merchant ID**
2. **Sandbox Account Name**
3. **Sandbox App ID** (for API authentication)
4. **Sandbox App Key** (for API authentication)

**Our Integration Details:**
- API Base URL (Sandbox): https://apis.sandbox.globalpay.com
- Integration Type: Hosted Payment Page (HPP)
- API Version: 2021-03-22
- Authentication: OAuth2 with app_id + app_key

**Testing Plan:**
Once we receive the sandbox credentials, we will:
1. Test access token generation
2. Test HPP link creation and payment flow
3. Test webhook notifications
4. Test both successful and failed payment scenarios
5. Verify 3D Secure authentication flow

**Questions:**
1. Should we create a sandbox app ourselves via the Developer Portal (https://developer.boipagateway.com), or will you provide sandbox credentials directly?
2. Are there separate sandbox portal login credentials needed?
3. Are there any IP whitelisting requirements for the sandbox environment?

We aim to complete sandbox testing this week and deploy to production by next week.

Thank you for your assistance. Please let me know if you need any additional information.

Best regards,

[Your Name]
Templeogue College Swim Pool
Email: info@tcsp.ie
Phone: [Your phone number]
```

---

## Alternative: Self-Service via Developer Portal

If BOIPA provides self-service sandbox app creation, you may be able to:

1. Log into https://developer.boipagateway.com
2. Navigate to "Apps" or "API Keys"
3. Click "Create New App"
4. Select "Sandbox" environment
5. Generate credentials automatically

**Check these sections in the portal:**
- Dashboard → API Keys
- Developer Settings → Applications
- Sandbox → Create App
- My Apps → New Application

---

## Follow-up if No Response

If no response within 2-3 business days, follow up with:

```
Subject: Follow-up: Sandbox Credentials Request - IE7200018387978

Dear BOIPA Support,

I am following up on my request from [DATE] for sandbox environment credentials.

Could you please confirm:
1. Have you received my request?
2. Is there a self-service option to create sandbox apps in the Developer Portal?
3. What is the typical turnaround time for sandbox credential provisioning?

We are eager to begin testing and would appreciate any guidance on the next steps.

Thank you,
[Your Name]
```

---

## Contact Information

**BOIPA Support Channels:**
- Email: support@boipa.com (or check your welcome email for support contact)
- Developer Portal Help: https://developer.boipagateway.com/support
- Portal: https://portal.boipagateway.com → Contact Support

**Your Previous BOIPA Contacts:**
- Angelica Miranda (provided production credentials on Dec 8, 2025)
- Check `/docs/communications/boipa/` for previous email contacts

---

## What to Do While Waiting

1. ✅ Review Developer Portal documentation: https://developer.boipagateway.com
2. ✅ Review test card numbers: docs/BOIPA_TEST_CARDS.md
3. ✅ Verify production code is ready (already implemented)
4. ✅ Set up ngrok tunnel for webhook testing: `ngrok http 8000`
5. ✅ Prepare test scenarios based on SANDBOX_TESTING_GUIDE.md

---

## Expected Response

BOIPA should provide either:

**Option A: Self-Service Instructions**
```
"Please log into the Developer Portal and create a sandbox app under
the 'Applications' section. Your credentials will be generated automatically."
```

**Option B: Direct Credentials**
```
Sandbox Merchant ID: MER_xxxxxxxxxxxxx
Sandbox Account Name: ECOMIE7200018387978_SANDBOX
Sandbox App ID: xxxxxxxxxxxxxxxxxx
Sandbox App Key: xxxxxxxxxxxxxxxxxx
```

---

## Timeline

- **Day 0 (Today):** Send email request
- **Day 1-2:** Await response or explore Developer Portal self-service
- **Day 3:** Follow up if no response
- **Day 4-5:** Receive credentials and begin testing
- **Day 6-7:** Complete sandbox testing
- **Day 8+:** Deploy to production

---