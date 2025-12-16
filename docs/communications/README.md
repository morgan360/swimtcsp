# Email Communications

This directory stores important email communications related to the TCSP project.

## Folder Structure

```
communications/
├── boipa/              # BOIPA payment gateway communications
│   └── [emails about API changes, credentials, support]
├── general/            # General project communications
│   └── [client emails, stakeholder communications]
└── README.md           # This file
```

## File Naming Convention

Use descriptive names with dates:
```
YYYY-MM-DD-brief-description.pdf
YYYY-MM-DD-brief-description.txt
```

### Examples:
- `2025-12-05-boipa-api-migration-notice.pdf`
- `2025-11-15-new-credentials.txt`
- `2025-12-01-support-response.pdf`

## How to Save Emails from Apple Mail

### Method 1: Save as PDF (Recommended)
1. Open the email in Apple Mail
2. **File → Export as PDF...** or **⌘P** then **PDF → Save as PDF**
3. Save to appropriate folder with descriptive name

### Method 2: Save as Plain Text
1. Open the email in Apple Mail
2. **File → Save As...** (or **⌘S**)
3. Format: Choose "Plain Text (.txt)"
4. Save to appropriate folder

### Method 3: Save as EML (Email Archive)
1. Open the email in Apple Mail
2. **File → Save As...** (or **⌘S**)
3. Format: Choose "Email Message (.eml)"
4. Save to appropriate folder
5. Note: .eml files preserve full email structure but require email client to open

## What to Save

### Priority Emails to Save:
- ✅ API migration notices
- ✅ New credentials or authentication details
- ✅ Breaking changes announcements
- ✅ Technical support responses
- ✅ Deadline notifications
- ✅ Contract or agreement updates

### Information to Extract:
When saving emails, note in this README:
- Date received
- Sender
- Key action items
- Deadlines
- Related documentation links

## BOIPA Migration Emails

Track BOIPA-related emails here:

| Date | Subject | Sender | Key Info | File |
|------|---------|--------|----------|------|
| _TBD_ | _Example: API Migration Notice_ | _BOIPA Support_ | _Deadline: Jan 2026_ | `boipa/2025-12-01-migration.pdf` |

## Notes

- **Do not commit sensitive credentials** to git - use `.env` instead
- If email contains API keys, extract them to settings and redact from saved file
- Update PAYMENT_MIGRATION.md based on email information