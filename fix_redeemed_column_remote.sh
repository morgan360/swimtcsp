#!/bin/bash
# Fix missing redeemed column on remote dev server
# Usage: ./fix_redeemed_column_remote.sh

set -e  # Exit on error

echo "🔧 Syncing migration history on dev server..."

ssh ssh.eu.pythonanywhere.com "cd dev-swimtcsp && \
  source ../.virtualenvs/dev-swimtcsp/bin/activate && \
  echo '📋 Checking migration status...' && \
  python manage.py showmigrations swims_orders --settings=config.development_settings | grep '0015' && \
  echo '🔄 Faking migration to sync history...' && \
  python manage.py migrate swims_orders 0015_order_redeemed --fake --settings=config.development_settings && \
  echo '✅ Migration history synced!'"

echo ""
echo "✨ Fix complete! The migration history has been synced on the dev server."