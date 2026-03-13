# DNS Migration to Cloudflare

This guide covers migrating the tcsp.ie domain from Hosting Ireland DNS to Cloudflare DNS while maintaining zero downtime for the website and email services.

## Table of Contents

- [Overview](#overview)
- [DNS Infrastructure](#dns-infrastructure)
- [Pre-Migration Checklist](#pre-migration-checklist)
- [Migration Steps](#migration-steps)
- [Post-Migration Verification](#post-migration-verification)
- [Mailchimp Domain Authentication](#mailchimp-domain-authentication)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedure](#rollback-procedure)

---

## Overview

**Migration Status:** ✅ **COMPLETED** - 2026-02-19

**Current Setup:**
- Domain Registrar: 101domain
- DNS Provider: Cloudflare (migrated from Hosting Ireland)
- Website Host: PythonAnywhere
- Email Provider: Microsoft 365
- Email Marketing: Mailchimp (domain authenticated)

**Migration Results:**
- ✅ DNS management moved to Cloudflare
- ✅ All existing services maintained (website, email, Microsoft 365)
- ✅ Mailchimp domain authentication complete (DKIM records active)
- ✅ Cloudflare security and performance features enabled

**Actual Downtime:** Zero - Migration completed successfully with no service interruption

---

## DNS Infrastructure

### Current Nameservers (Hosting Ireland)
```
NS1.WEBHOSTINGIRELAND.IE
NS2.WEBHOSTINGIRELAND.IE
NS3.WEBHOSTINGIRELAND.IE
```

### New Nameservers (Cloudflare)
After adding tcsp.ie to Cloudflare, you'll receive custom nameservers like:
```
ava.ns.cloudflare.com
tim.ns.cloudflare.com
```
(Your exact nameservers will be different)

---

## Pre-Migration Checklist

Before starting the migration, ensure you have:

- [ ] Access to 101domain account (domain registrar)
- [ ] Cloudflare account created (free tier is sufficient)
- [ ] All current DNS records documented (see below)
- [ ] PythonAnywhere CNAME target: `webapp-23139.eu.pythonanywhere.com`
- [ ] Microsoft 365 admin access (if needed for verification)
- [ ] Backup of all DNS records (screenshots or export)
- [ ] Scheduled migration during low-traffic period (recommended)

### Current DNS Records Backup

Run this command to verify current DNS before migration:
```bash
dig tcsp.ie ANY
nslookup -type=ANY tcsp.ie
```

Or use online tools:
- https://mxtoolbox.com/SuperTool.aspx?action=mx%3atcsp.ie
- https://dnschecker.org/all-dns-records-of-domain.php?query=tcsp.ie

---

## Migration Steps

### Phase 1: Set Up Cloudflare DNS

#### Step 1.1: Add Domain to Cloudflare

1. Log into your Cloudflare account at https://dash.cloudflare.com
2. Click "Add a Site"
3. Enter `tcsp.ie`
4. Select the **Free plan**
5. Click "Continue"

#### Step 1.2: Review Auto-Imported Records

Cloudflare will scan and import some existing DNS records. Review them carefully - they may be incomplete or incorrect.

#### Step 1.3: Add/Verify All DNS Records

**CRITICAL:** Manually verify and add ALL the following records in Cloudflare:

##### Website Records

```
Type: CNAME
Name: @
Target: webapp-23139.eu.pythonanywhere.com
Proxy status: DNS only (grey cloud)
TTL: Auto
```

```
Type: CNAME
Name: www
Target: webapp-23139.eu.pythonanywhere.com
Proxy status: DNS only (grey cloud)
TTL: Auto
```

**Note:** Keep proxy OFF (grey cloud) for PythonAnywhere. Cloudflare's CNAME flattening will handle the root (@) domain correctly.

##### Email Records (Microsoft 365)

**MX Record:**
```
Type: MX
Name: @
Priority: 0
Mail server: tcsp-ie.mail.protection.outlook.com
TTL: Auto
```

**SPF Record:**
```
Type: TXT
Name: @
Content: v=spf1 include:spf.protection.outlook.com include:servers.mcsv.net -all
TTL: Auto
```
*Note: This includes both Microsoft 365 and Mailchimp authorization*

**DKIM Records (Microsoft 365):**
```
Type: CNAME
Name: selector1._domainkey
Target: selector1-tcsp-ie._domainkey.tcspie.onmicrosoft.com
Proxy status: DNS only
TTL: Auto

Type: CNAME
Name: selector2._domainkey
Target: selector2-tcsp-ie._domainkey.tcspie.onmicrosoft.com
Proxy status: DNS only
TTL: Auto
```

⚠️ **Important:** Your current DNS has `selector1` pointing to `selector2`'s target (configuration error). This will be corrected in Cloudflare.

**DMARC Record:**
```
Type: TXT
Name: _dmarc
Content: v=DMARC1;p=none;sp=none;adkim=r;aspf=r;pct=100;fo=0;rf=afrf;ri=86400
TTL: Auto
```

##### Microsoft 365 Service Records

**Autodiscover (Outlook clients):**
```
Type: CNAME
Name: autodiscover
Target: autodiscover.outlook.com
Proxy status: DNS only
TTL: Auto
```

**Skype for Business / Teams:**
```
Type: CNAME
Name: sip
Target: sipdir.online.lync.com
Proxy status: DNS only
TTL: Auto

Type: CNAME
Name: lyncdiscover
Target: webdir.online.lync.com
Proxy status: DNS only
TTL: Auto
```

**Mobile Device Management:**
```
Type: CNAME
Name: enterpriseregistration
Target: enterpriseregistration.windows.net
Proxy status: DNS only
TTL: Auto

Type: CNAME
Name: enterpriseenrollment
Target: enterpriseenrollment.manage.microsoft.com
Proxy status: DNS only
TTL: Auto
```

#### Step 1.4: Note Your Cloudflare Nameservers

After adding all records, Cloudflare will display your assigned nameservers. **Write these down** - you'll need them for the next phase.

Example:
```
ava.ns.cloudflare.com
tim.ns.cloudflare.com
```

---

### Phase 2: Change Nameservers at 101domain

⚠️ **IMPORTANT:** Only proceed after ALL DNS records are correctly configured in Cloudflare.

#### Step 2.1: Access 101domain DNS Settings

1. Log into your 101domain account
2. Navigate to your domain: `tcsp.ie`
3. Find the **"Name Servers"** section
4. Click **"Edit Name Servers"**

#### Step 2.2: Update Nameservers

You'll see a warning that you're using external nameservers - this is expected.

1. Remove all 3 Hosting Ireland nameservers:
   - `NS1.WEBHOSTINGIRELAND.IE`
   - `NS2.WEBHOSTINGIRELAND.IE`
   - `NS3.WEBHOSTINGIRELAND.IE`

2. Add your 2 Cloudflare nameservers (from Step 1.4)

3. **Save changes**

#### Step 2.3: Wait for Propagation

- **Cloudflare verification:** 5 minutes to 24 hours (usually quick)
- **Global DNS propagation:** 1-48 hours (typically 2-4 hours)

You can monitor propagation status at:
- Cloudflare dashboard (will show "Active" when verified)
- https://www.whatsmydns.net/#NS/tcsp.ie

---

## Post-Migration Verification

### Immediate Checks (After Cloudflare Shows "Active")

#### 1. Website Accessibility

```bash
# Test main domain
curl -I https://tcsp.ie

# Test www subdomain
curl -I https://www.tcsp.ie
```

Or visit in browser:
- https://tcsp.ie
- https://www.tcsp.ie

**Expected:** Site loads correctly with PythonAnywhere content

#### 2. DNS Resolution

```bash
# Check nameservers
dig NS tcsp.ie

# Check A/CNAME records
dig tcsp.ie
dig www.tcsp.ie

# Check MX records
dig MX tcsp.ie
```

**Expected:** Should show Cloudflare nameservers and correct record values

#### 3. Email Testing

**Send Test Email:**
1. Send email FROM `swimming@tcsp.ie`
2. Check it arrives (not in spam)

**Receive Test Email:**
1. Send email TO `swimming@tcsp.ie` from external address
2. Verify it's received in Microsoft 365

**Check Email Authentication:**
Visit https://mxtoolbox.com and test:
- MX Lookup: `tcsp.ie`
- SPF Record Check: `tcsp.ie`
- DMARC Lookup: `tcsp.ie`

**Expected Results:**
- MX points to `tcsp-ie.mail.protection.outlook.com`
- SPF includes `spf.protection.outlook.com` and `servers.mcsv.net`
- DMARC policy is configured
- All tests show green checkmarks

#### 4. Microsoft 365 Services

Test these services still work:
- Outlook Web App: https://outlook.office.com
- Email sync on mobile devices
- Teams/Skype for Business (if used)
- Autodiscover for new Outlook clients

---

## Mailchimp Domain Authentication

After DNS migration is complete and verified, authenticate your domain in Mailchimp to fix the email deliverability warning.

### Step 1: Initiate Authentication in Mailchimp

1. Log into Mailchimp
2. Go to **Settings** → **Domains**
3. Find `tcsp.ie` in the list
4. Click **"Authenticate now"** (or "Verify domain")

### Step 2: Add DKIM Records to Cloudflare

Mailchimp will provide 2-3 CNAME records similar to:

```
Type: CNAME
Name: k1._domainkey
Target: dkim.mcsv.net

Type: CNAME
Name: k2._domainkey
Target: dkim2.mcsv.net
```

Add these records in Cloudflare:
1. Go to Cloudflare dashboard → DNS
2. Click "Add record"
3. Enter the CNAME records exactly as Mailchimp provides
4. Proxy status: DNS only (grey cloud)
5. Save

### Step 3: Verify in Mailchimp

1. Return to Mailchimp → Settings → Domains
2. Click **"Verify"** next to your domain
3. Wait for verification (can take up to 48 hours, usually within 1 hour)

**Expected Result:** Domain shows as "Verified" with a green checkmark

### Step 4: Test Email Deliverability

Send a test campaign or email to verify:
- Emails are less likely to go to spam
- Email headers show DKIM signatures
- Bounce rate improves over time

---

## Troubleshooting

### Website Not Loading

**Symptom:** tcsp.ie shows error or old content

**Solutions:**

1. **Check DNS propagation:**
   ```bash
   dig tcsp.ie @8.8.8.8
   ```
   If still shows old DNS, wait longer for propagation

2. **Verify CNAME record in Cloudflare:**
   - Should point to `webapp-23139.eu.pythonanywhere.com`
   - Proxy status should be OFF (grey cloud)

3. **Clear browser cache:**
   ```
   Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
   ```

4. **Check PythonAnywhere:**
   - Log into PythonAnywhere
   - Verify web app is running
   - Check WSGI file configuration

### Email Not Working

**Symptom:** Can't send or receive email

**Solutions:**

1. **Verify MX record:**
   ```bash
   dig MX tcsp.ie
   ```
   Should return: `tcsp-ie.mail.protection.outlook.com`

2. **Check SPF record:**
   ```bash
   dig TXT tcsp.ie
   ```
   Should include: `v=spf1 include:spf.protection.outlook.com`

3. **Wait for propagation:**
   Email DNS changes can take longer (up to 24 hours)

4. **Test with external tool:**
   https://mxtoolbox.com/emailhealth/tcsp.ie

### Cloudflare Shows "Pending"

**Symptom:** Cloudflare dashboard shows domain as pending verification

**Solutions:**

1. **Verify nameservers at 101domain:**
   - Log into 101domain
   - Check nameservers match Cloudflare's exactly
   - No typos in nameserver entries

2. **Wait longer:**
   - Can take up to 24 hours for verification
   - Check Cloudflare "Overview" tab for status

3. **Click "Re-check nameservers":**
   - In Cloudflare dashboard
   - Click "Re-check now" button

### Mailchimp Domain Won't Verify

**Symptom:** Mailchimp shows domain as not verified

**Solutions:**

1. **Check DKIM records in Cloudflare:**
   ```bash
   dig CNAME k1._domainkey.tcsp.ie
   dig CNAME k2._domainkey.tcsp.ie
   ```

2. **Verify exact record values:**
   - Match exactly what Mailchimp provided
   - No extra spaces or characters

3. **Wait for DNS propagation:**
   - Can take up to 48 hours
   - Try verifying again after 2-4 hours

4. **Remove and re-add records:**
   - Delete DKIM records in Cloudflare
   - Wait 5 minutes
   - Add them again exactly as Mailchimp specifies

---

## Rollback Procedure

If critical issues occur during migration, you can rollback to Hosting Ireland DNS.

### Emergency Rollback Steps

1. **Log into 101domain**
2. **Navigate to Name Servers**
3. **Click "Restore name servers to default settings"**
   - This reverts to 101domain's default nameservers
4. **Manually set back to Hosting Ireland:**
   ```
   NS1.WEBHOSTINGIRELAND.IE
   NS2.WEBHOSTINGIRELAND.IE
   NS3.WEBHOSTINGIRELAND.IE
   ```
5. **Save changes**
6. **Wait for propagation** (1-4 hours)

**Note:** Original DNS records at Hosting Ireland should still be intact, so services will resume working.

### Partial Rollback (Hybrid Approach)

If only specific services fail:

1. Keep Cloudflare nameservers active
2. Fix the problematic DNS record in Cloudflare dashboard
3. No need to change nameservers back

---

## Best Practices

### DNS Management Going Forward

1. **Always use Cloudflare dashboard** for DNS changes
2. **Document changes** in this file or project documentation
3. **Test changes** with `dig` or online tools before assuming they work
4. **Monitor email deliverability** regularly

### Cloudflare Settings Recommendations

1. **SSL/TLS:** Set to "Full" (not "Full (strict)" - PythonAnywhere limitation)
2. **Always Use HTTPS:** Enable to redirect HTTP to HTTPS
3. **Security Level:** Medium (adjust if needed)
4. **Caching Level:** Standard (don't cache HTML for Django app)
5. **Auto Minify:** Enable for JavaScript, CSS (but test thoroughly)

### Monitoring

Set up monitoring for:
- Website uptime: https://uptimerobot.com or Cloudflare monitoring
- Email deliverability: Mailchimp reports
- DNS changes: Cloudflare audit logs

---

## Additional Resources

### DNS Tools
- **MX Toolbox:** https://mxtoolbox.com/SuperTool.aspx
- **DNS Checker:** https://dnschecker.org
- **What's My DNS:** https://www.whatsmydns.net
- **DNS Propagation:** https://dnspropagation.net

### Documentation
- **Cloudflare DNS Docs:** https://developers.cloudflare.com/dns/
- **Microsoft 365 DNS:** https://docs.microsoft.com/en-us/microsoft-365/admin/get-help-with-domains/
- **Mailchimp Authentication:** https://mailchimp.com/help/verify-a-domain/

### Support Contacts
- **101domain Support:** Via account dashboard
- **Cloudflare Support:** https://support.cloudflare.com
- **Microsoft 365 Support:** https://admin.microsoft.com/AdminPortal/Home#/support
- **PythonAnywhere Support:** https://www.pythonanywhere.com/support/

---

## Migration History

| Date | Action | Performed By | Notes |
|------|--------|--------------|-------|
| 2026-02-19 | Initial migration to Cloudflare | Morgan | Successfully migrated from Hosting Ireland DNS |
| 2026-02-19 | Mailchimp DKIM records added | Morgan | Added k2 and k3 DKIM records, verified and working |
| 2026-02-19 | Cloudflare nameservers activated | Morgan | Changed nameservers at 101domain to adaline/brodie.ns.cloudflare.com |
| 2026-02-19 | Redirect rule configured | Morgan | Added redirect from tcsp.ie → www.tcsp.ie (matching numscoil.ie setup) |
| 2026-02-19 | Security settings configured | Morgan | Enabled Bot Fight Mode, Email Obfuscation, automated security level |

---

## Notes

- This migration does not affect the domain registration - tcsp.ie remains registered with 101domain
- PythonAnywhere hosting is unaffected - only DNS provider changes
- Microsoft 365 email service is unaffected - only DNS records are moved
- All services should continue working throughout the migration with zero downtime
- Keep Hosting Ireland account active for 30 days after migration as a safety net

## Post-Migration Issues Encountered and Resolved

### Issue 1: DNS Propagation Delay
**Problem:** After configuring Cloudflare DNS, the site still showed Hosting Ireland maintenance page
**Cause:** DNS propagation delay - local systems cached old Hosting Ireland nameservers
**Resolution:** Cleared DNS cache and waited for global propagation (2-4 hours)
**Lesson:** Always clear browser and system DNS cache after nameserver changes

### Issue 2: Root Domain Not Working
**Problem:** www.tcsp.ie worked but tcsp.ie showed maintenance page
**Cause:** Missing Cloudflare redirect rule (numscoil.ie had one, tcsp.ie didn't)
**Resolution:** Created redirect rule in Cloudflare: tcsp.ie → www.tcsp.ie with proxy enabled
**Configuration:**
- Rule name: Redirect to www
- Condition: Hostname equals tcsp.ie
- Action: Dynamic redirect to `concat("https://www.tcsp.ie", http.request.uri.path)`
- Status: 301 (permanent redirect)

### Issue 3: Mailchimp Domain Verification
**Problem:** Mailchimp showed Cloudflare authorization dialog
**Status:** User chose to authorize Cloudflare integration for easier verification
**Note:** Alternative manual verification also available via Mailchimp DKIM records

## Security Configuration Applied

All security settings configured on 2026-02-19:

- ✅ **SSL/TLS Mode:** Full (not Full Strict - PythonAnywhere limitation)
- ✅ **Always Use HTTPS:** Enabled
- ✅ **Automatic HTTPS Rewrites:** Enabled
- ✅ **Security Level:** Automated (always protected)
- ✅ **Bot Fight Mode:** Enabled
- ✅ **Email Address Obfuscation:** Enabled
- ✅ **Browser Integrity Check:** Enabled (via automated security)

## Final Configuration Summary

**Cloudflare Nameservers:**
- adaline.ns.cloudflare.com
- brodie.ns.cloudflare.com

**DNS Records:** All records configured with proxy enabled (orange cloud) to match numscoil.ie setup

**Redirect Rules:** Root domain redirects to www subdomain

**Total Migration Time:** 1 day (including DNS propagation)

**Actual Downtime:** 0 minutes
