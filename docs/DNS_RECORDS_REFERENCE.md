# DNS Records Reference

Quick reference for all active DNS records for `tcsp.ie` configured in Cloudflare.

**Last Updated:** 2026-02-19

**Migration Status:** ✅ Fully migrated to Cloudflare DNS - All records active and verified

---

## Website Records

| Type  | Name | Target/Value                          | Proxy | TTL  | Purpose                    |
|-------|------|---------------------------------------|-------|------|----------------------------|
| CNAME | @    | webapp-23139.eu.pythonanywhere.com    | Off   | Auto | Main website (tcsp.ie)     |
| CNAME | www  | webapp-23139.eu.pythonanywhere.com    | Off   | Auto | WWW subdomain              |

**Notes:**
- Proxy is OFF (grey cloud) for PythonAnywhere compatibility
- Both records point to the same PythonAnywhere CNAME target
- Cloudflare handles CNAME flattening for the root (@) domain automatically

---

## Email Records (Microsoft 365)

### MX Record

| Type | Name | Priority | Mail Server                             | TTL  |
|------|------|----------|-----------------------------------------|------|
| MX   | @    | 0        | tcsp-ie.mail.protection.outlook.com     | Auto |

**Purpose:** Routes incoming email to Microsoft 365

---

### SPF Record

| Type | Name | Content                                                                      | TTL  |
|------|------|------------------------------------------------------------------------------|------|
| TXT  | @    | `v=spf1 include:spf.protection.outlook.com include:servers.mcsv.net -all`   | Auto |

**Purpose:** Authorizes Microsoft 365 and Mailchimp to send email on behalf of tcsp.ie

**Breakdown:**
- `v=spf1` - SPF version 1
- `include:spf.protection.outlook.com` - Authorizes Microsoft 365
- `include:servers.mcsv.net` - Authorizes Mailchimp
- `-all` - Strict policy (reject all other sources)

---

### DKIM Records (Microsoft 365)

| Type  | Name                 | Target                                            | Proxy | TTL  |
|-------|----------------------|---------------------------------------------------|-------|------|
| CNAME | selector1._domainkey | selector1-tcsp-ie._domainkey.tcspie.onmicrosoft.com | Off   | Auto |
| CNAME | selector2._domainkey | selector2-tcsp-ie._domainkey.tcspie.onmicrosoft.com | Off   | Auto |

**Purpose:** Email authentication signatures from Microsoft 365

**Note:** These records are managed by Microsoft 365 and should not be modified manually.

---

### DMARC Record

| Type | Name   | Content                                                                   | TTL  |
|------|--------|---------------------------------------------------------------------------|------|
| TXT  | _dmarc | `v=DMARC1;p=none;sp=none;adkim=r;aspf=r;pct=100;fo=0;rf=afrf;ri=86400`   | Auto |

**Purpose:** Email security policy for handling unauthenticated emails

**Breakdown:**
- `v=DMARC1` - DMARC version 1
- `p=none` - Policy: monitoring mode (don't reject, just report)
- `sp=none` - Subdomain policy: same as main policy
- `adkim=r` - Relaxed DKIM alignment
- `aspf=r` - Relaxed SPF alignment
- `pct=100` - Apply policy to 100% of messages
- `fo=0` - Forensic reporting options
- `rf=afrf` - Report format
- `ri=86400` - Report interval (daily)

**Recommendation:** After 30 days of monitoring, consider changing `p=none` to `p=quarantine` or `p=reject` for stronger security.

---

## Microsoft 365 Service Records

### Autodiscover (Outlook Configuration)

| Type  | Name        | Target                  | Proxy | TTL  |
|-------|-------------|-------------------------|-------|------|
| CNAME | autodiscover| autodiscover.outlook.com| Off   | Auto |

**Purpose:** Automatic Outlook client configuration for new users

---

### Skype for Business / Teams

| Type  | Name         | Target                     | Proxy | TTL  |
|-------|--------------|----------------------------|-------|------|
| CNAME | sip          | sipdir.online.lync.com     | Off   | Auto |
| CNAME | lyncdiscover | webdir.online.lync.com     | Off   | Auto |

**Purpose:**
- `sip` - Session Initiation Protocol for voice/video
- `lyncdiscover` - Auto-configuration for Skype/Teams

---

### Mobile Device Management (MDM)

| Type  | Name                    | Target                                   | Proxy | TTL  |
|-------|-------------------------|------------------------------------------|-------|------|
| CNAME | enterpriseregistration  | enterpriseregistration.windows.net       | Off   | Auto |
| CNAME | enterpriseenrollment    | enterpriseenrollment.manage.microsoft.com| Off   | Auto |

**Purpose:** Microsoft Intune device enrollment and management

---

## Mailchimp Records

### DKIM Records (Mailchimp Email Authentication)

**Status:** ✅ Active and verified (added 2026-02-19)

| Type  | Name             | Target          | Proxy | TTL  |
|-------|------------------|-----------------|-------|------|
| CNAME | k2._domainkey    | dkim2.mcsv.net  | Off   | Auto |
| CNAME | k3._domainkey    | dkim3.mcsv.net  | Off   | Auto |

**Purpose:** Email authentication signatures from Mailchimp for improved deliverability

**Verification:**
```bash
dig CNAME k2._domainkey.tcsp.ie
dig CNAME k3._domainkey.tcsp.ie
```

**Note:** Mailchimp provided k2 and k3 selectors (not k1 and k2 as typically expected)

---

## DNS Management

### Where Records are Managed

- **Registrar:** 101domain (domain ownership, nameserver settings)
- **DNS Provider:** Cloudflare (all DNS records managed here)
- **Access:** https://dash.cloudflare.com

### Nameservers

Domain `tcsp.ie` uses Cloudflare nameservers:
- adaline.ns.cloudflare.com
- brodie.ns.cloudflare.com

To verify current nameservers:
```bash
dig NS tcsp.ie
```

### Cloudflare Redirect Rules

**Redirect: tcsp.ie → www.tcsp.ie**

A redirect rule is configured in Cloudflare (Rules → Redirect Rules) to redirect the root domain to the www subdomain:

- **Rule name:** Redirect to www
- **Condition:** Hostname equals `tcsp.ie`
- **Action:** Dynamic redirect
- **Expression:** `concat("https://www.tcsp.ie", http.request.uri.path)`
- **Status code:** 301 (permanent redirect)
- **Proxy required:** Yes (orange cloud must be enabled on tcsp.ie A record)

This matches the configuration used for numscoil.ie.

---

## DNS Verification Commands

### Check All Records

```bash
# Nameservers
dig NS tcsp.ie

# Website (A/CNAME)
dig tcsp.ie
dig www.tcsp.ie

# Email (MX)
dig MX tcsp.ie

# SPF
dig TXT tcsp.ie

# DKIM (Microsoft 365)
dig CNAME selector1._domainkey.tcsp.ie
dig CNAME selector2._domainkey.tcsp.ie

# DMARC
dig TXT _dmarc.tcsp.ie

# Autodiscover
dig CNAME autodiscover.tcsp.ie
```

### Online Verification Tools

- **All DNS Records:** https://mxtoolbox.com/SuperTool.aspx?action=mx%3atcsp.ie
- **Email Health Check:** https://mxtoolbox.com/emailhealth/tcsp.ie
- **DNS Propagation:** https://www.whatsmydns.net/#A/tcsp.ie
- **DMARC Check:** https://mxtoolbox.com/DMARC.aspx

---

## Common DNS Changes

### Updating PythonAnywhere Target

If PythonAnywhere CNAME changes in the future:

1. Log into Cloudflare dashboard
2. Go to DNS settings
3. Edit both `@` and `www` CNAME records
4. Update target to new PythonAnywhere value
5. Save (propagation is typically instant with Cloudflare)

### Adding New Subdomains

Example: Adding `blog.tcsp.ie` pointing to external service

```
Type: CNAME
Name: blog
Target: [service-target.example.com]
Proxy: Off (or On, depending on service requirements)
TTL: Auto
```

### Emergency DNS Changes

For urgent DNS changes:
1. Changes in Cloudflare propagate quickly (seconds to minutes)
2. Always verify with `dig` command after making changes
3. Clear browser cache or test in incognito mode
4. Use https://www.whatsmydns.net to check global propagation

---

## Security Considerations

### Current Security Posture

- ✅ SPF configured (prevents email spoofing)
- ✅ DKIM configured for Microsoft 365 (email authentication)
- ✅ DKIM configured for Mailchimp (email authentication)
- ✅ DMARC in monitoring mode (email policy enforcement)
- ⚠️ DMARC in `p=none` mode (consider upgrading to `p=quarantine` after monitoring)

### Recommendations

1. **Monitor DMARC reports** for 30 days
2. **Upgrade DMARC policy** from `p=none` to `p=quarantine` after validation
3. **Enable Cloudflare security features:**
   - SSL/TLS: Full mode
   - Always Use HTTPS: Enabled
   - Security Level: Medium
4. **Regular audits:** Review DNS records quarterly

---

## Troubleshooting Quick Reference

| Issue | Check | Fix |
|-------|-------|-----|
| Website not loading | `dig tcsp.ie` | Verify CNAME points to correct PythonAnywhere target |
| Email not sending | `dig MX tcsp.ie` | Verify MX record points to Microsoft 365 |
| Email marked as spam | Check SPF/DKIM/DMARC | Ensure all email auth records are present |
| Outlook autoconfigure fails | `dig autodiscover.tcsp.ie` | Verify autodiscover CNAME exists |
| Mailchimp deliverability warning | Mailchimp → Domains | Add Mailchimp DKIM records |

---

## Contact Information

### Service Providers

- **Domain Registrar:** 101domain - Account dashboard
- **DNS Provider:** Cloudflare - https://dash.cloudflare.com
- **Web Hosting:** PythonAnywhere - https://www.pythonanywhere.com
- **Email Provider:** Microsoft 365 - https://admin.microsoft.com
- **Email Marketing:** Mailchimp - https://mailchimp.com

### Support Resources

- **Cloudflare Docs:** https://developers.cloudflare.com/dns/
- **Microsoft 365 DNS Help:** https://docs.microsoft.com/en-us/microsoft-365/admin/get-help-with-domains/
- **Mailchimp Authentication:** https://mailchimp.com/help/verify-a-domain/

---

## Change Log

| Date       | Change                              | Updated By | Notes                                    |
|------------|-------------------------------------|------------|------------------------------------------|
| 2026-02-17 | Document created                    | Morgan     | Initial DNS records documentation        |
| 2026-02-19 | Migrated to Cloudflare              | Morgan     | Nameservers changed from Hosting Ireland |
| 2026-02-19 | Mailchimp DKIM added                | Morgan     | k2 and k3 DKIM records added and verified |

---

## Notes

- Keep this document updated when DNS records change
- All DNS changes should be made through Cloudflare dashboard only
- Before making changes, document the current state
- Test changes with `dig` commands before assuming they work
- For major DNS changes, schedule during low-traffic periods
