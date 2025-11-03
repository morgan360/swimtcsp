# Deployment Guide

This document covers deployment procedures for the TCSP Django application to PythonAnywhere.

## Environments

- **Dev Server:** https://dev-morganmck.eu.pythonanywhere.com
- **Production:** https://www.tcsp.ie

## Quick Deployment

### Deploy to Dev Server

From your local project directory:

```bash
./deploy-to-dev.sh
```

This automated script handles the entire deployment process.

## What the Deployment Script Does

The `deploy-to-dev.sh` script performs the following steps automatically:

1. **Stash local changes** - Saves any uncommitted changes on the server
2. **Pull latest code** - Fetches and merges from GitHub `origin/main`
3. **Activate virtual environment** - Switches to the dev virtualenv
4. **Run migrations** - Applies any new database migrations
5. **Collect static files** - Gathers all static assets to the static directory
6. **Reload web app** - Touches the WSGI file to restart the application

## Manual Deployment Steps

If you need to deploy manually or troubleshoot issues:

### 1. SSH into PythonAnywhere

```bash
ssh ssh.eu.pythonanywhere.com
```

### 2. Navigate to Project Directory

```bash
cd dev-swimtcsp
```

### 3. Check Git Status

```bash
git status
git log --oneline -5
```

### 4. Pull Latest Code

```bash
# Stash any local changes first (if needed)
git stash

# Pull from main branch
git pull origin main
```

### 5. Activate Virtual Environment

```bash
source ../.virtualenvs/dev-swimtcsp/bin/activate
```

### 6. Run Database Migrations

```bash
python manage.py migrate --settings=config.development_settings
```

### 7. Collect Static Files

```bash
python manage.py collectstatic --noinput --settings=config.development_settings
```

### 8. Reload Web Application

```bash
# Touch the WSGI file to trigger a reload
touch /var/www/dev-morganmck_eu_pythonanywhere_com_wsgi.py
```

## Common Issues and Solutions

### Migration Conflicts

If you encounter migration file conflicts during `git pull`:

```bash
# Remove the conflicting local migration
rm path/to/conflicting/migration.py

# Pull again
git pull origin main
```

### Static Files Not Updating

```bash
# Clear the static files directory
rm -rf static_files/*

# Re-collect
python manage.py collectstatic --noinput --settings=config.development_settings
```

### Web App Not Reloading

```bash
# Manually touch the WSGI file
touch /var/www/dev-morganmck_eu_pythonanywhere_com_wsgi.py

# Or use PythonAnywhere's web interface:
# Go to Web tab → Click "Reload" button
```

### Database Connection Issues

Check your `.env` file settings match the PythonAnywhere MySQL configuration:

```bash
# View current database settings (be careful with credentials)
python manage.py diffsettings | grep DATABASE
```

## Pre-Deployment Checklist

Before deploying to production, ensure:

- [ ] All tests pass locally: `python manage.py test`
- [ ] New migrations are created: `python manage.py makemigrations --check`
- [ ] Static files build successfully: `npm run build`
- [ ] Code has been pushed to GitHub
- [ ] No sensitive data in committed files
- [ ] Dependencies updated in `requirements.txt` if needed

## Post-Deployment Verification

After deployment, verify:

1. **Site loads correctly** - Visit the URL and check homepage
2. **Database access works** - Try logging in
3. **Static files serve** - Check CSS/JS are loading
4. **Admin panel accessible** - Test `/admin/` or custom admin routes
5. **Payment integration** - Test BOIPA integration (use sandbox)
6. **Key features work** - Book a lesson, view dashboards, etc.

## SSH Configuration

Your local SSH config (`~/.ssh/config`) should contain:

```
Host ssh.eu.pythonanywhere.com
  HostName ssh.eu.pythonanywhere.com
  User morganmck
```

## PythonAnywhere File Locations

- **Project directory:** `/home/morganmck/dev-swimtcsp`
- **Virtual environment:** `/home/morganmck/.virtualenvs/dev-swimtcsp`
- **WSGI file:** `/var/www/dev-morganmck_eu_pythonanywhere_com_wsgi.py`
- **Static files:** `/home/morganmck/dev-swimtcsp/static_files`

## Rollback Procedure

If a deployment causes issues:

```bash
# SSH into server
ssh ssh.eu.pythonanywhere.com

# Navigate to project
cd dev-swimtcsp

# Check recent commits
git log --oneline -10

# Rollback to previous commit (replace COMMIT_HASH)
git reset --hard COMMIT_HASH

# Re-run migrations if needed (migrate backwards)
python manage.py migrate app_name migration_name

# Reload app
touch /var/www/dev-morganmck_eu_pythonanywhere_com_wsgi.py
```

## Support Resources

- **PythonAnywhere Help:** https://help.pythonanywhere.com/
- **PythonAnywhere SSH:** https://help.pythonanywhere.com/pages/SSHAccess
- **Django Deployment:** https://docs.djangoproject.com/en/5.2/howto/deployment/

## Notes

- The `deploy-to-dev.sh` script is git-ignored to keep server-specific configurations local
- Always test on dev before deploying to production
- Keep your SSH keys secure and never commit them to the repository