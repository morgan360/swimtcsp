# Production Deployment Guide

This guide covers deploying updates from dev-swimtcsp to the live production site (www.tcsp.ie).

## Quick Start

```bash
# 1. Ensure all changes are committed and pushed
git status
git push origin main

# 2. Test on dev server first
./deploy-to-dev.sh

# 3. After testing, deploy to production
./deploy-to-production.sh
```

## Before You Begin

### Prerequisites

1. **All changes committed to GitHub main branch**
   ```bash
   git status  # Should show "nothing to commit, working tree clean"
   ```

2. **Changes tested on dev server**
   - Visit https://dev-morganmck.eu.pythonanywhere.com
   - Test all new features
   - Verify BOIPA payments work
   - Test chatbot functionality

3. **Production credentials ready**
   - SSH access to production PythonAnywhere
   - Production `.env` file configured
   - BOIPA API keys (live, not sandbox)
   - OpenAI API key with sufficient quota

4. **Backup plan ready**
   - Database backup location verified
   - Rollback procedure understood

---

## Automated Deployment

### Using the Production Deployment Script

The `deploy-to-production.sh` script automates the entire deployment process.

#### Step 1: Configure the Script (First Time Only)

Edit `deploy-to-production.sh` and update these variables:

```bash
PRODUCTION_DIR="swimtcsp"          # Your production directory on PythonAnywhere
PRODUCTION_VENV="../.virtualenvs/swimtcsp"  # Path to production virtualenv
PRODUCTION_WSGI="/var/www/morganmck_pythonanywhere_com_wsgi.py"  # WSGI file path
PRODUCTION_SETTINGS="config.production_settings"  # Production settings module
```

Also configure the database backup command (around line 85):

```bash
# Update with your actual credentials
mysqldump -u YOUR_DB_USER -pYOUR_DB_PASSWORD YOUR_DB_NAME > $BACKUP_FILE
```

#### Step 2: Run the Deployment

```bash
./deploy-to-production.sh
```

The script will:

1. **Pre-flight checks:**
   - Verify you're on main branch
   - Check for uncommitted changes
   - Ensure local is synced with GitHub
   - Show recent commits
   - Ask for confirmation

2. **Deploy to production:**
   - Create database backup
   - Enable maintenance mode
   - Pull latest code
   - Update dependencies
   - Run migrations
   - Rebuild FAQ embeddings
   - Collect static files
   - Reload web app
   - Disable maintenance mode

3. **Show post-deployment checklist**

#### What Happens During Deployment

```
╔════════════════════════════════════════════════════════════╗
║        TCSP PRODUCTION DEPLOYMENT SCRIPT                   ║
║        Target: www.tcsp.ie                                 ║
╚════════════════════════════════════════════════════════════╝

⚠️  PRE-FLIGHT CHECKS
✅ Git checks passed

⚠️  WARNING: You are about to deploy to PRODUCTION
   This will affect live users at www.tcsp.ie

Latest commits to be deployed:
6e4b1646 Merge pull request #196 from morgan360/navbar-style-update
39f7e2f8 Merge pull request #197 from morgan360/stagnation-filtering

Are you sure you want to continue? [y/N]: y

═══════════════════════════════════════════════════════
STEP 1: Database Backup
═══════════════════════════════════════════════════════
📦 Creating database backup...
✅ Backup created: backups/backup_20251114_143022.sql

═══════════════════════════════════════════════════════
STEP 2: Enable Maintenance Mode
═══════════════════════════════════════════════════════
🔒 Enabling maintenance mode...
✅ Maintenance mode enabled
   Users will see maintenance page

[... continues through all steps ...]

╔════════════════════════════════════════════════════════════╗
║  ✅ DEPLOYMENT COMPLETE!                                   ║
╚════════════════════════════════════════════════════════════╝
```

---

## Manual Deployment

If you prefer to deploy manually or need to troubleshoot:

### 1. Create Database Backup

```bash
ssh ssh.eu.pythonanywhere.com
cd swimtcsp
mkdir -p backups
mysqldump -u YOUR_DB_USER -p YOUR_DB_NAME > backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup is not empty
ls -lh backups/
```

### 2. Enable Maintenance Mode

```bash
source ../.virtualenvs/swimtcsp/bin/activate
python manage.py maintenance_mode on --settings=config.production_settings
```

**What users see:**
- Regular users: Maintenance page
- Staff/superusers: Full site access (for testing)
- Admin panels remain accessible

### 3. Pull Latest Code

```bash
git stash  # Save any local changes
git pull origin main
git log --oneline -10  # Verify correct commits
```

### 4. Update Dependencies

```bash
pip install -r requirements.txt --upgrade
```

### 5. Run Database Migrations

```bash
python manage.py migrate --settings=config.production_settings
```

**Check migrations before running:**
```bash
python manage.py showmigrations --settings=config.production_settings
```

### 6. Rebuild FAQ Embeddings

```bash
python manage.py rebuild_faq_embeddings --settings=config.production_settings
```

**Options:**
- `--force` - Re-embed all FAQs even if embeddings exist
- `--delete-orphans` - Remove FAQs not in faq.yaml

**Expected output:**
```
🔄 Starting FAQ Rebuild Process...

📄 Loaded 47 FAQs from faq.yaml
🤖 Using embedding model: text-embedding-3-small
🔧 Embedding: What should I bring to a public swim?...
  ✅ Re-embedded
[...]

============================================================
✅ FAQ Rebuild Complete!
============================================================
📊 Summary:
   • New FAQs created: 0
   • Existing FAQs updated: 0
   • Skipped (already embedded): 0
   • Errors: 0

📈 Database Status:
   • Total FAQs in database: 47
   • FAQs with embeddings: 47

✅ All FAQs have embeddings!
```

### 7. Collect Static Files

```bash
python manage.py collectstatic --noinput --settings=config.production_settings
```

### 8. Reload Web Application

```bash
touch /var/www/morganmck_pythonanywhere_com_wsgi.py
```

Or use PythonAnywhere web interface:
- Go to Web tab → Click "Reload" button

### 9. Disable Maintenance Mode

```bash
python manage.py maintenance_mode off --settings=config.production_settings
```

**Site is now live!**

---

## Post-Deployment Testing

### Immediate Checks (First 5 Minutes)

1. **Site loads:**
   ```
   https://www.tcsp.ie
   ```

2. **Static files work:**
   - Check CSS is loading (navbar styles)
   - Check JavaScript is working
   - Open browser console for errors

3. **Authentication:**
   - Login with email/password
   - Test Google OAuth login
   - Logout and login again

### Critical User Flow Testing (15 Minutes)

#### Test Lesson Booking Flow

1. Browse lessons
2. Add lesson to cart
3. Apply coupon (test new coupon features)
4. View discount display (new feature)
5. Proceed to checkout
6. **Complete test payment** (use small amount)
7. Verify order created
8. Check enrollment appears in dashboard

#### Test BOIPA Payment Integration

```bash
# Monitor payment webhooks
ssh ssh.eu.pythonanywhere.com
cd swimtcsp
tail -f logs/boipa.log  # If you have logging set up
```

**Check:**
- [ ] Payment page loads
- [ ] Payment processes successfully
- [ ] Webhook received and processed
- [ ] Order status updated to "paid"
- [ ] LessonEnrollment created
- [ ] Confirmation email sent (if configured)

#### Test Chatbot

1. **Public Swim Chat:**
   ```
   https://www.tcsp.ie/chat/public-swim/
   ```
   - Ask: "When is the next swim?"
   - Ask: "What should I bring?"
   - Verify FAQ matching works

2. **Lesson Chat:**
   ```
   https://www.tcsp.ie/chat/public-lesson/
   ```
   - Ask: "What levels are available?"
   - Ask: "When does the term start?"
   - Verify responses are accurate

3. **Check chatbot queries are logged:**
   ```bash
   python manage.py shell --settings=config.production_settings
   >>> from chatbot.models import ChatbotQuery
   >>> ChatbotQuery.objects.order_by('-timestamp')[:5]
   ```

### Admin Panel Testing (10 Minutes)

Test new features deployed:

1. **Lessons Admin:**
   ```
   https://www.tcsp.ie/lessonsadmin/
   ```
   - Check weekly pricing display (new feature)
   - Verify lessons load correctly

2. **Stagnation Filtering:**
   - Navigate to stagnation page
   - Test level filter (new feature)
   - Test day filter (new feature)
   - Test export filtered enrollments (new feature)

3. **Coupons Admin:**
   ```
   https://www.tcsp.ie/couponsadmin/
   ```
   - Create test coupon
   - Verify multi-use balance tracking (bug fix)
   - Test coupon usage context restrictions

### Monitor for Issues (30 Minutes)

#### Watch Error Logs

```bash
ssh ssh.eu.pythonanywhere.com

# Django error log
tail -f /var/www/logs/error.log

# Or if you have custom logging
tail -f swimtcsp/logs/django.log
```

#### Check Django Admin Logs

```bash
python manage.py shell --settings=config.production_settings
>>> from django.contrib.admin.models import LogEntry
>>> LogEntry.objects.order_by('-action_time')[:10]
```

#### Monitor BOIPA Transactions

Check your BOIPA dashboard for:
- Payment success rate
- Any failed transactions
- Webhook delivery status

#### Check OpenAI API Usage

- Visit OpenAI dashboard
- Verify chatbot requests are processing
- Check you're not hitting rate limits
- Monitor token usage

---

## Rollback Procedure

If critical issues are found after deployment:

### Quick Rollback

```bash
ssh ssh.eu.pythonanywhere.com
cd swimtcsp

# 1. Enable maintenance mode
source ../.virtualenvs/swimtcsp/bin/activate
python manage.py maintenance_mode on --settings=config.production_settings

# 2. Check recent commits
git log --oneline -10

# 3. Rollback to previous version
git reset --hard <PREVIOUS_COMMIT_HASH>

# 4. Reload app
touch /var/www/morganmck_pythonanywhere_com_wsgi.py

# 5. Disable maintenance mode
python manage.py maintenance_mode off --settings=config.production_settings
```

### Rollback with Database Restore

If migrations caused issues:

```bash
# 1. Enable maintenance mode (as above)

# 2. Restore database from backup
mysql -u YOUR_DB_USER -p YOUR_DB_NAME < backups/backup_20251114_143022.sql

# 3. Rollback code (as above)

# 4. Run migrations to match code
python manage.py migrate --settings=config.production_settings

# 5. Reload and disable maintenance (as above)
```

---

## FAQ Management Commands

### Rebuild FAQ Embeddings

**When to use:**
- After deployment (to ensure embeddings are current)
- When faq.yaml is updated
- When switching OpenAI embedding models
- When FAQ embeddings seem stale

**Basic usage:**
```bash
python manage.py rebuild_faq_embeddings --settings=config.production_settings
```

**Force re-embed all:**
```bash
python manage.py rebuild_faq_embeddings --force --settings=config.production_settings
```

**Clean up orphaned FAQs:**
```bash
python manage.py rebuild_faq_embeddings --delete-orphans --settings=config.production_settings
```

### Import FAQs (Without Re-embedding)

```bash
python manage.py import_faqs --settings=config.production_settings
```

### Embed Only New FAQs

```bash
python manage.py embed_new_faqs --settings=config.production_settings
```

---

## Troubleshooting

### Maintenance Mode Won't Enable

```bash
# Check if django-maintenance-mode is installed
pip list | grep maintenance

# Try manual mode
python manage.py shell --settings=config.production_settings
>>> from django.core.cache import cache
>>> cache.set('maintenance_mode', True)
```

### Migrations Fail

```bash
# Check migration status
python manage.py showmigrations --settings=config.production_settings

# See migration plan
python manage.py migrate --plan --settings=config.production_settings

# Fake a migration if needed (CAREFUL!)
python manage.py migrate --fake app_name migration_number --settings=config.production_settings
```

### FAQ Embedding Fails

```bash
# Check OpenAI API key
python manage.py shell --settings=config.production_settings
>>> import os
>>> os.getenv('OPENAI_API_KEY')

# Test OpenAI connection
>>> from openai import OpenAI
>>> client = OpenAI()
>>> response = client.embeddings.create(input=["test"], model="text-embedding-3-small")
>>> len(response.data[0].embedding)  # Should be 1536
```

### Static Files Not Loading

```bash
# Check static files path
python manage.py findstatic css/styles.css --settings=config.production_settings

# Force re-collect
rm -rf static_files/*
python manage.py collectstatic --noinput --settings=config.production_settings

# Check STATIC_ROOT in settings
python manage.py diffsettings --settings=config.production_settings | grep STATIC
```

### BOIPA Payments Not Working

1. **Check API credentials:**
   ```bash
   # Verify environment variables
   cat .env | grep BOIPA
   ```

2. **Check webhook URL is registered with BOIPA**

3. **Test webhook manually:**
   ```bash
   # Check webhook endpoint is accessible
   curl -X POST https://www.tcsp.ie/boipa/webhook/
   ```

4. **Check BOIPA logs:**
   - Visit BOIPA dashboard
   - Check transaction history
   - Verify webhook delivery status

---

## Deployment Checklist

Use this checklist for every production deployment:

### Pre-Deployment

- [ ] All changes committed to main branch
- [ ] All changes pushed to GitHub
- [ ] Changes tested on dev server
- [ ] New features documented
- [ ] Breaking changes identified
- [ ] Migration plan reviewed
- [ ] Rollback plan prepared
- [ ] Team notified of deployment window

### During Deployment

- [ ] Database backup created and verified
- [ ] Maintenance mode enabled
- [ ] Code pulled from GitHub
- [ ] Dependencies updated
- [ ] Migrations run successfully
- [ ] FAQ embeddings rebuilt
- [ ] Static files collected
- [ ] Web app reloaded
- [ ] Maintenance mode disabled

### Post-Deployment

- [ ] Site loads correctly
- [ ] Authentication works
- [ ] Booking flow tested
- [ ] BOIPA payments tested
- [ ] Chatbot functionality verified
- [ ] Admin panels accessible
- [ ] New features tested
- [ ] Static files loading
- [ ] No errors in logs
- [ ] Team notified of completion

---

## Emergency Contacts

- **PythonAnywhere Support:** help@pythonanywhere.com
- **BOIPA Support:** [your BOIPA support contact]
- **OpenAI Support:** https://help.openai.com

---

## Related Documentation

- [DEPLOYMENT.md](../DEPLOYMENT.md) - Dev server deployment
- [CLAUDE.md](../CLAUDE.md) - Project overview
- [README.md](../README.md) - Getting started

---

**Last Updated:** 2025-11-14
**Deployment Script Version:** 1.0