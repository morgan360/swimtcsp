# DNS Pre-Migration Audit

**Audit Date:** 2026-02-17
**Domain:** tcsp.ie
**Current DNS Provider:** Hosting Ireland
**Target DNS Provider:** Cloudflare

---

## Current DNS Configuration

### Nameservers (Hosting Ireland)
```
ns1.webhostingireland.ie
ns2.webhostingireland.ie
ns3.webhostingireland.ie
ns4.webhostingireland.eu
```

---

## Website Records

### Main Domain (tcsp.ie)
```
Type: A
Value: 91.210.235.113 (Hosting Ireland IP)
TTL: 14400
```
**Status:** ⚠️ Points to Hosting Ireland instead of PythonAnywhere
**Action Required:** Change to CNAME pointing to PythonAnywhere

### WWW Subdomain (www.tcsp.ie)
```
Type: CNAME
Target: webapp-23139.eu.pythonanywhere.com
Resolves to: 18.194.5.49 (AWS Frankfurt - PythonAnywhere)
TTL: 14400
```
**Status:** ✅ Correct
**Action Required:** Keep as-is in Cloudflare

---

## Email Records (Microsoft 365)

### MX Records
```
Priority: 0
Server: tcsp-ie.mail.protection.outlook.com
TTL: 14400
```
**Status:** ✅ Correct

```
Priority: 32767
Server: ms71453849.msv1.invalid
TTL: 14400
```
**Status:** ❌ Invalid/obsolete record
**Action Required:** Do not migrate this record

### SPF Record
```
Type: TXT
Value: v=spf1 ip4:91.210.235.113 include:spf.webhostingireland.ie +include:spf.protection.outlook.com -all
TTL: 14400
```
**Status:** ⚠️ Contains obsolete Hosting Ireland references
**Issues:**
- Includes Hosting Ireland IP (91.210.235.113)
- Includes Hosting Ireland SPF (spf.webhostingireland.ie)
- Missing Mailchimp authorization (servers.mcsv.net)

**New SPF Record for Cloudflare:**
```
v=spf1 include:spf.protection.outlook.com include:servers.mcsv.net -all
```

### DKIM Records (Microsoft 365)

**selector1._domainkey:**
```
Type: CNAME
Current Target: selector2-tcsp-ie._domainkey.tcspie.onmicrosoft.com
TTL: 14400
```
**Status:** ❌ Configuration Error
**Issue:** Points to selector2's target instead of selector1
**Correct Target:** `selector1-tcsp-ie._domainkey.tcspie.onmicrosoft.com`

**selector2._domainkey:**
```
Type: CNAME
Target: selector2-tcsp-ie._domainkey.tcspie.onmicrosoft.com
TTL: 14400
```
**Status:** ✅ Correct

### DMARC Record
```
Type: TXT
Name: _dmarc
Value: v=DMARC1;p=none;sp=none;adkim=r;aspf=r;pct=100;fo=0;rf=afrf;ri=86400
TTL: 14400
```
**Status:** ✅ Correct
**Note:** Currently in monitoring mode (p=none)

---

## Microsoft 365 Service Records

### Autodiscover
```
Type: CNAME
Name: autodiscover
Target: autodiscover.outlook.com
TTL: 14400
```
**Status:** ✅ Correct

### Skype for Business / Teams

**SIP:**
```
Type: CNAME
Name: sip
Target: sipdir.online.lync.com
TTL: 14400
```
**Status:** ✅ Correct

**Lyncdiscover:**
```
Type: CNAME
Name: lyncdiscover
Target: webdir.online.lync.com
TTL: 14400
```
**Status:** ✅ Correct

### Mobile Device Management

**Enterprise Registration:**
```
Type: CNAME
Name: enterpriseregistration
Target: enterpriseregistration.windows.net
TTL: 14400
```
**Status:** ✅ Correct

**Enterprise Enrollment:**
```
Type: CNAME
Name: enterpriseenrollment
Target: enterpriseenrollment.manage.microsoft.com
TTL: 14400
```
**Status:** ✅ Correct

---

## Mailchimp Records

### DKIM (Email Authentication)
**Status:** ❌ Not Configured
**Action Required:** Add after Cloudflare migration (via Mailchimp domain authentication)

Expected records:
```
Type: CNAME
Name: k1._domainkey
Target: dkim.mcsv.net (to be confirmed by Mailchimp)

Type: CNAME
Name: k2._domainkey
Target: dkim2.mcsv.net (to be confirmed by Mailchimp)
```

---

## Migration Impact Analysis

### What Will Be Fixed
1. ✅ Main domain (tcsp.ie) will point to PythonAnywhere
2. ✅ selector1 DKIM record will have correct target
3. ✅ Invalid MX record will be removed
4. ✅ SPF will be cleaned up (remove Hosting Ireland, add Mailchimp)
5. ✅ Mailchimp DKIM will be added (improves email deliverability)

### What Will Stay the Same
- All Microsoft 365 email functionality
- WWW subdomain (already correct)
- All Microsoft 365 service records
- DMARC policy
- No email downtime expected

### Potential Risks
- **Low Risk:** DNS propagation delay (1-4 hours typical)
- **Mitigated:** All email records will be identical, so email continues working
- **Mitigated:** PythonAnywhere already serving www subdomain

---

## Pre-Migration Checklist

- [x] DNS records documented
- [x] Current configuration audited
- [x] Issues identified
- [x] PythonAnywhere target confirmed (webapp-23139.eu.pythonanywhere.com)
- [ ] Cloudflare account created
- [ ] Migration guide reviewed
- [ ] Low-traffic migration window scheduled
- [ ] Stakeholders notified
- [ ] Rollback plan understood

---

## DNS Verification Commands Used

```bash
# Full DNS query
dig tcsp.ie ANY
nslookup -type=ANY tcsp.ie

# Website records
dig tcsp.ie
dig www.tcsp.ie

# Email records
dig MX tcsp.ie
dig TXT tcsp.ie

# DKIM records
dig TXT selector1._domainkey.tcsp.ie
dig TXT selector2._domainkey.tcsp.ie

# DMARC record
dig TXT _dmarc.tcsp.ie

# Microsoft 365 service records
dig CNAME autodiscover.tcsp.ie
dig CNAME sip.tcsp.ie
dig CNAME lyncdiscover.tcsp.ie
dig CNAME enterpriseregistration.tcsp.ie
dig CNAME enterpriseenrollment.tcsp.ie
```

---

## Recommendations

### Immediate (During Migration)
1. Fix selector1 DKIM configuration error
2. Update SPF record to remove Hosting Ireland references
3. Point main domain to PythonAnywhere
4. Do not migrate invalid MX record

### Post-Migration (Within 1 Week)
1. Authenticate domain in Mailchimp
2. Add Mailchimp DKIM records
3. Monitor email deliverability
4. Verify all services working correctly

### Long-Term (Within 1 Month)
1. Monitor DMARC reports
2. Consider upgrading DMARC policy from `p=none` to `p=quarantine`
3. Enable Cloudflare security features (WAF, DDoS protection)
4. Set up monitoring alerts for DNS changes

---

## Notes

- This audit was performed on 2026-02-17 at 21:33 GMT
- All DNS records use TTL of 14400 seconds (4 hours)
- Current DNS is served by Hosting Ireland nameservers
- Email is hosted by Microsoft 365 (working correctly)
- Website hosting is split: www on PythonAnywhere, root on Hosting Ireland
- No critical issues that would prevent migration
- Migration can proceed with confidence

---

## Next Steps

1. Review this audit
2. Create Cloudflare account
3. Follow [DNS Migration Guide](/docs/DNS_MIGRATION_TO_CLOUDFLARE.md)
4. Schedule migration during low-traffic period
5. Execute migration
6. Verify all services post-migration
7. Authenticate Mailchimp domain

---

## Support Contacts

- **Domain Registrar:** 101domain
- **Current DNS:** Hosting Ireland
- **Target DNS:** Cloudflare
- **Web Hosting:** PythonAnywhere
- **Email Provider:** Microsoft 365
- **Email Marketing:** Mailchimp
