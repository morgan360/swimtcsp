# BOIPA New API - Production Deployment Checklist

**Date Created:** December 16, 2025
**Status:** Ready for Production Deployment
**Ticket:** BOIPA-6530

---

## 🔴 CRITICAL: Live Payment Gateway Migration

**This deployment connects your site to the LIVE BOIPA IPG (Integrated Payment Gateway).**

- ❌ NOT sandbox/test environment
- ✅ REAL payment processing
- ✅ REAL card transactions
- ✅ REAL customer charges

**Before proceeding:**
- Confirm BOIPA has activated your production credentials
- Test checkout flow during maintenance mode
- Have rollback plan ready
- Monitor closely for first 24 hours

---

## ✅ Pre-Deployment Checklist

### 1. Verify Production Credentials

Confirm you have the following production credentials from BOIPA:

```bash
BOIPA_CLIENT_ID=EVOIE0CHY0745
BOIPA_ACCOUNT_NAME=ECOMIE7200018387978
BOIPA_APP_ID=3rVzj4c9YTwOsBwU9d6wWfM6G2XfV2Dm
BOIPA_APP_KEY=TVo8VVsSu4JWb49s
```

**Source:** Email from Angelica Miranda, December 8, 2025
**Portal Access:** https://portal.boipagateway.com (Username: TempSwimPool)

### 2. Sandbox Testing Complete

- [x] OAuth2 token generation tested
- [x] HPP link creation tested
- [x] Payment processing tested (local)
- [x] Payment processing tested (dev server)
- [x] Session error handling implemented
- [x] Orders marked paid correctly
- [x] Enrollments created correctly
- [x] Emails sent correctly
- [x] User redirect working

### 3. Code Changes Committed

All code changes are in the main branch:
- [x] `boipa/payment_functions.py` - OAuth2 authentication
- [x] `boipa/views.py` - Payment response handling with CSRF exempt
- [x] `utils/middleware.py` - PaymentGatewaySessionMiddleware
- [x] `config/base_settings.py` - Middleware added
- [x] `config/development_settings.py` - New BOIPA variables

---

## 🚀 Production Deployment Steps

### Step 1: Backup Current Production

Before making any changes:

```bash
# On production server (PythonAnywhere)
cd ~/swimtcsp
git stash  # Save any uncommitted changes
git tag pre-boipa-migration-$(date +%Y%m%d)  # Create a tag
git push origin --tags
```

### Step 2: Update Production Environment Variables

**File:** `/home/morganmck/swimtcsp/.env` on production PythonAnywhere

**IMPORTANT:** Keep BOTH old and new variables for easy rollback!

```bash
# =============================================================================
# NEW BOIPA Production Credentials (OAuth2 API)
# =============================================================================
BOIPA_CLIENT_ID=EVOIE0CHY0745
BOIPA_ACCOUNT_NAME=ECOMIE7200018387978
BOIPA_ACCOUNT_ID=TRA_ef38c091212340a5b4731856b71038b2
BOIPA_APP_ID=3rVzj4c9YTwOsBwU9d6wWfM6G2XfV2Dm
BOIPA_APP_KEY=TVo8VVsSu4JWb49s

# Production API Endpoints (NO "sandbox" in URLs)
BOIPA_API_BASE_URL=https://apis.boipagateway.com
BOIPA_ACCESS_TOKEN_URL=https://apis.boipagateway.com/ucp/accesstoken
BOIPA_HPP_LINKS_URL=https://apis.boipagateway.com/ucp/links
BOIPA_TRANSACTIONS_URL=https://apis.boipagateway.com/ucp/transactions
BOIPA_API_VERSION=2021-03-22

# Production domain for callbacks
NGROK=https://www.tcsp.ie

# =============================================================================
# OLD BOIPA Credentials (Legacy API) - KEEP FOR ROLLBACK
# =============================================================================
# BOIPA_MERCHANT_ID=your_old_merchant_id
# BOIPA_PASSWORD=your_old_password
# BOIPA_TOKEN_URL=your_old_token_url
# HPP_FORM=your_old_hpp_form
# BRAND_ID=your_old_brand_id
# BOIPA_PAYMENT_URL=your_old_payment_url
```

**CRITICAL:**
- Make sure there's NO trailing slash on `NGROK`!
- Keep old variables commented out for easy rollback
- The `production_settings.py` will use the new variables by default

### Step 3: Verify Production Settings File

Check `config/production_settings.py` reads these variables correctly.

If it doesn't have BOIPA variables defined, add them similar to `development_settings.py`:

```python
# --- BOIPA (New API - OAuth2) ---
BOIPA_CLIENT_ID        = config('BOIPA_CLIENT_ID')
BOIPA_MERCHANT_ID      = config('BOIPA_CLIENT_ID')  # Alias for compatibility
BOIPA_ACCOUNT_NAME     = config('BOIPA_ACCOUNT_NAME')
BOIPA_ACCOUNT_ID       = config('BOIPA_ACCOUNT_ID')
BOIPA_APP_ID           = config('BOIPA_APP_ID')
BOIPA_APP_KEY          = config('BOIPA_APP_KEY')
BOIPA_API_BASE_URL     = config('BOIPA_API_BASE_URL')
BOIPA_ACCESS_TOKEN_URL = config('BOIPA_ACCESS_TOKEN_URL')
BOIPA_HPP_LINKS_URL    = config('BOIPA_HPP_LINKS_URL')
BOIPA_TRANSACTIONS_URL = config('BOIPA_TRANSACTIONS_URL')
BOIPA_API_VERSION      = config('BOIPA_API_VERSION', default='2021-03-22')
NGROK                  = config('NGROK', default='https://www.tcsp.ie').rstrip('/')
```

### Step 4: Enable Maintenance Mode

**CRITICAL:** Put site in maintenance mode before making changes:

```bash
# SSH to production
ssh ssh.eu.pythonanywhere.com
cd ~/swimtcsp

# Activate virtual environment
source ../.virtualenvs/swimtcsp/bin/activate

# Enable maintenance mode
python manage.py maintenance_mode on --settings=config.production_settings
```

**What happens:**
- Regular users see maintenance page
- Staff/superusers can still access site for testing
- Admin panels remain accessible

### Step 5: Pull Latest Code on Production

```bash
cd ~/swimtcsp
git fetch origin
git checkout main
git pull origin main
```

### Step 6: Reload Production Web App

1. Go to PythonAnywhere **Web** tab
2. Find your production app (www.tcsp.ie or tcsp.ie)
3. Click green **"Reload"** button

### Step 7: Test as Staff User

**Before disabling maintenance mode:**

1. Log in as staff/superuser
2. Test checkout flow quickly
3. Verify BOIPA IPG (live gateway) redirects correctly
4. **DO NOT complete payment yet** - just verify redirect works

### Step 8: Disable Maintenance Mode

```bash
# After verifying redirect works
python manage.py maintenance_mode off --settings=config.production_settings
```

**Site is now live with new BOIPA IPG!**

### Step 9: Monitor Logs

Watch for any startup errors:

```bash
# On PythonAnywhere, check error log
tail -f /var/log/tcsp.pythonanywhere.com.error.log
```

Also check your application logs:
```bash
tail -f ~/swimtcsp/logs/payments.log
```

---

## 🧪 Production Testing

### Test 1: Small Real Transaction (€1.00)

**IMPORTANT:** Before processing real customer payments, do a test with a **real card** for **€1.00**:

1. Log into production site as a test user
2. Add a swimling
3. Book a lesson for €1.00 (or minimum amount)
4. Complete checkout
5. Use a **real credit/debit card** (not a test card!)
6. Monitor the entire flow:
   - Payment redirect to BOIPA
   - Payment completion
   - Redirect back to site
   - Check order marked paid in database
   - Check enrollment created
   - Check email sent
   - Check BOIPA portal shows transaction

7. **Verify in BOIPA Portal:**
   - Log into https://portal.boipagateway.com
   - Check transaction appears
   - Verify amount is correct

8. **Issue refund for test transaction:**
   - Either via BOIPA portal
   - Or test the refund functionality in your admin

### Test 2: Monitor for Issues

After first successful test:
- Watch logs for 24 hours
- Check for any errors
- Verify all payments processing correctly

---

## ⚠️ Rollback Plan

If something goes wrong, you can easily revert to the old BOIPA API:

### Option 1: Quick Rollback (Settings File Only - FASTEST)

**Time:** ~30 seconds

Edit `config/production_settings.py` on the server:

1. SSH to production: `ssh ssh.eu.pythonanywhere.com`
2. Edit the file: `nano ~/swimtcsp/config/production_settings.py`
3. Find the BOIPA section (around line 18-45)
4. Comment out the NEW API section (add `#` at start of each line)
5. Uncomment the OLD API section (remove `#` from each line)
6. Save and exit (Ctrl+X, Y, Enter)
7. Reload web app via PythonAnywhere Web tab

**Result:** Site immediately reverts to old BOIPA API

### Option 2: Environment Variable Rollback

**Time:** ~2 minutes

Edit `/home/morganmck/swimtcsp/.env` on the server:

1. SSH to production: `ssh ssh.eu.pythonanywhere.com`
2. Edit the file: `nano ~/swimtcsp/.env`
3. Comment out all NEW BOIPA variables (add `#` at start)
4. Uncomment all OLD BOIPA variables (remove `#`)
5. Save and exit
6. Edit `config/production_settings.py` to revert BOIPA section
7. Reload web app

**Result:** Complete reversion including credentials

### Option 3: Full Git Rollback

**Time:** ~5 minutes (includes code reversion)

```bash
# SSH to production
ssh ssh.eu.pythonanywhere.com
cd ~/swimtcsp

# Revert to pre-migration state
git checkout pre-boipa-migration-YYYYMMDD  # Use the tag from Step 1

# Reload web app
touch /var/www/morganmck_pythonanywhere_com_wsgi.py
```

**Or** use PythonAnywhere Web tab → Reload button

**Result:** Complete code and configuration rollback

---

### After Rollback - Verify

1. **Test checkout flow** - Ensure payments work with old API
2. **Check logs** - Verify no errors
3. **Monitor for 1 hour** - Ensure stability
4. **Contact BOIPA** - Report issues with new API if needed

---

## 📋 Post-Deployment Verification

After deployment, verify:

- [ ] Site loads without errors
- [ ] User can add items to cart
- [ ] Checkout process works
- [ ] Payment redirect to BOIPA works
- [ ] Payment completion works
- [ ] User redirected back successfully
- [ ] Orders marked paid
- [ ] Enrollments created
- [ ] Emails sent
- [ ] BOIPA portal shows transactions

---

## 🔧 Troubleshooting

### Issue: Blank page after payment

**Likely cause:** Missing `NGROK` variable or trailing slash
**Fix:** Check `.env` has `NGROK=https://www.tcsp.ie` (no trailing slash)

### Issue: Payment not processing

**Check:**
1. Logs: `~/swimtcsp/logs/payments.log`
2. BOIPA credentials are production (not sandbox)
3. URLs don't have "sandbox" in them
4. `PaymentGatewaySessionMiddleware` is in middleware stack

### Issue: SessionInterrupted errors

**Solution:** This is expected and handled by `PaymentGatewaySessionMiddleware`
**Check:** Middleware is placed after `SessionMiddleware` in `config/base_settings.py`

### Issue: 403 CSRF errors

**Solution:** `@csrf_exempt` should be on `payment_response` view
**Check:** `boipa/views.py` line 62

---

## 📞 Support Contacts

**If issues arise:**

1. **BOIPA Support:**
   - Email: ecommerce@boipa.com
   - Phone: 1800 806 670
   - Portal: https://portal.boipagateway.com → Support

2. **Your Documentation:**
   - API Docs: `docs/BOIPA_NEW_API_DOCUMENTATION.md`
   - Test Results: `docs/SANDBOX_TEST_RESULTS.md`
   - This Checklist: `docs/PRODUCTION_DEPLOYMENT_CHECKLIST.md`

---

## ✅ Final Checks Before Going Live

- [ ] Confirmed with BOIPA that production credentials are active
- [ ] Tested €1 transaction successfully
- [ ] Verified transaction appears in BOIPA portal
- [ ] Verified refund process works (optional)
- [ ] Backed up current production state
- [ ] Rollback plan tested and ready
- [ ] Team notified of deployment
- [ ] Monitoring in place for first 24 hours

---

## 📅 Deployment Timeline

**Recommended:**
1. **Day 1 Morning:** Deploy to production, test €1 transaction
2. **Day 1:** Monitor all transactions closely
3. **Day 2:** Continue monitoring, verify all emails sent
4. **Day 3:** Normal operations, spot check transactions

**Avoid:**
- Deploying on Friday afternoon
- Deploying during peak booking times
- Deploying without someone available to monitor

---

**Created by:** Claude Code Assistant
**Last Updated:** December 16, 2025
**Status:** Ready for production deployment pending BOIPA confirmation
