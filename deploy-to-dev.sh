#!/bin/bash
# Deployment script for PythonAnywhere dev server
# Usage: ./deploy-to-dev.sh

set -e  # Exit on error

echo "🚀 Starting deployment to dev-morganmck.eu.pythonanywhere.com..."

# Deploy to PythonAnywhere dev server
ssh ssh.eu.pythonanywhere.com "cd dev-swimtcsp && \
  echo '📦 Stashing local changes...' && \
  git stash && \
  echo '⬇️  Pulling latest code from GitHub...' && \
  git pull origin main && \
  echo '🐍 Activating virtual environment...' && \
  source ../.virtualenvs/dev-swimtcsp/bin/activate && \
  echo '💾 Running database migrations...' && \
  python manage.py migrate --settings=config.development_settings && \
  echo '📂 Collecting static files...' && \
  python manage.py collectstatic --noinput --settings=config.development_settings && \
  echo '🔄 Reloading web app...' && \
  touch /var/www/dev-morganmck_eu_pythonanywhere_com_wsgi.py && \
  echo '✅ Deployment complete!'"

echo ""
echo "✨ Your dev server has been updated!"
echo "🌐 Visit: https://dev-morganmck.eu.pythonanywhere.com"