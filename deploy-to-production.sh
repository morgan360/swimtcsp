#!/bin/bash
# Production Deployment Script for TCSP
# Usage: ./deploy-to-production.sh
#
# IMPORTANT: This script deploys to LIVE production (www.tcsp.ie)
# Use with caution and only after testing on dev!

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - UPDATE THESE VALUES
PRODUCTION_HOST="ssh.eu.pythonanywhere.com"
PRODUCTION_USER="morganmck"
PRODUCTION_DIR="swimtcsp"  # UPDATE THIS to your production directory name
PRODUCTION_VENV="../.virtualenvs/swimtcsp"  # UPDATE THIS to your production venv path
# The WSGI file that actually serves www.tcsp.ie. This previously pointed at
# /var/www/morganmck_pythonanywhere_com_wsgi.py, which is a 0-byte unused file —
# so every deploy "reloaded" nothing and the new code only took effect whenever
# PythonAnywhere happened to recycle the worker.
PRODUCTION_WSGI="/var/www/www_tcsp_ie_wsgi.py"
PRODUCTION_SETTINGS="config.production_settings"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║        TCSP PRODUCTION DEPLOYMENT SCRIPT                   ║${NC}"
echo -e "${BLUE}║        Target: www.tcsp.ie                                 ║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Pre-flight checks
echo -e "${YELLOW}⚠️  PRE-FLIGHT CHECKS${NC}"
echo ""

# Check if on main branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}❌ You are not on the main branch (currently on: $CURRENT_BRANCH)${NC}"
    echo -e "${YELLOW}   Switch to main branch before deploying to production${NC}"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}❌ You have uncommitted changes${NC}"
    echo -e "${YELLOW}   Commit and push all changes before deploying${NC}"
    exit 1
fi

# Check if local is up to date with remote
git fetch origin main
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo -e "${RED}❌ Your local main is not in sync with origin/main${NC}"
    echo -e "${YELLOW}   Push your changes or pull latest before deploying${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Git checks passed${NC}"
echo ""

# Confirmation prompt (skipped for automated deployment)
echo -e "${RED}⚠️  WARNING: You are about to deploy to PRODUCTION${NC}"
echo -e "${YELLOW}   This will affect live users at www.tcsp.ie${NC}"
echo ""
echo "Latest commits to be deployed:"
git log --oneline -5
echo ""
echo -e "${YELLOW}Proceeding with automated deployment (no confirmation required)${NC}"
echo ""
# Confirmation skipped - uncomment below to re-enable interactive confirmation:
# read -p "$(echo -e ${YELLOW}Are you sure you want to continue? [y/N]:${NC} )" -n 1 -r
# echo ""
# if [[ ! $REPLY =~ ^[Yy]$ ]]; then
#     echo -e "${BLUE}Deployment cancelled${NC}"
#     exit 0
# fi

echo ""
echo -e "${GREEN}🚀 Starting Production Deployment...${NC}"
echo ""

# Deploy to Production - Build script with variable replacement
DEPLOY_SCRIPT=$(cat << 'ENDSSH'
set -e

# Color codes for remote output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

cd PRODUCTION_DIR_PLACEHOLDER

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 1: Database Backup${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

mkdir -p backups
BACKUP_FILE="backups/backup_$(date +%Y%m%d_%H%M%S).sql.gz"
echo -e "${BLUE}📦 Creating database backup...${NC}"

# Credentials come from Django settings so this stays correct if they change.
# MYSQL_PWD rather than -p on the command line, which would expose the password
# in the process list.
source PRODUCTION_VENV_PLACEHOLDER/bin/activate
eval "$(python - <<'PYEOF'
import os, django, shlex
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PRODUCTION_SETTINGS_PLACEHOLDER")
django.setup()
from django.conf import settings
db = settings.DATABASES["default"]
for key in ("NAME", "USER", "HOST", "PASSWORD"):
    print(f"DB_{key}={shlex.quote(str(db[key]))}")
PYEOF
)"

# --no-tablespaces: the shared MySQL user has no PROCESS privilege, and without
# this mysqldump emits an access-denied warning for tablespaces.
# PIPESTATUS, because a mysqldump failure would otherwise be hidden by gzip
# exiting 0 on the truncated stream it received.
MYSQL_PWD="$DB_PASSWORD" mysqldump \
    --user="$DB_USER" --host="$DB_HOST" \
    --single-transaction --quick --no-tablespaces \
    --default-character-set=utf8mb4 \
    "$DB_NAME" | gzip > "$BACKUP_FILE"
DUMP_STATUS=${PIPESTATUS[0]}
if [ "$DUMP_STATUS" -ne 0 ]; then
    echo -e "${RED}❌ mysqldump exited ${DUMP_STATUS} — aborting before any change${NC}"
    exit 1
fi

# A backup that exists but is empty is worse than none, because it looks fine.
BACKUP_BYTES=$(stat -c %s "$BACKUP_FILE" 2>/dev/null || stat -f %z "$BACKUP_FILE")
if [ "$BACKUP_BYTES" -lt 10000 ]; then
    echo -e "${RED}❌ Backup is only ${BACKUP_BYTES} bytes — aborting${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Backup written: $BACKUP_FILE ($(( BACKUP_BYTES / 1024 )) KB)${NC}"
# Keep the 5 most recent: these are ~30 MB each against a shared disk quota.
ls -1t backups/backup_*.sql.gz 2>/dev/null | tail -n +6 | xargs -r rm --
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 2: Enable Maintenance Mode${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

source PRODUCTION_VENV_PLACEHOLDER/bin/activate

echo -e "${BLUE}🔒 Enabling maintenance mode...${NC}"
python manage.py maintenance_mode on --settings=PRODUCTION_SETTINGS_PLACEHOLDER || {
    echo -e "${RED}❌ Failed to enable maintenance mode${NC}"
    exit 1
}
echo -e "${GREEN}✅ Maintenance mode enabled${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 3: Pull Latest Code${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

echo -e "${BLUE}📦 Stashing local changes...${NC}"
git stash
echo -e "${BLUE}⬇️  Pulling latest code...${NC}"
git pull origin main
git log --oneline -1
echo -e "${GREEN}✅ Code updated${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 4: Update Dependencies${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

echo -e "${BLUE}🐍 Installing/updating packages...${NC}"
pip install -r requirements.txt --upgrade --quiet
echo -e "${GREEN}✅ Dependencies updated${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 5: Run Database Migrations${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

echo -e "${BLUE}💾 Running migrations...${NC}"
python manage.py migrate --settings=PRODUCTION_SETTINGS_PLACEHOLDER
echo -e "${GREEN}✅ Migrations complete${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 6: Rebuild FAQ Embeddings${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

echo -e "${BLUE}🤖 Re-vectorizing FAQs...${NC}"
# Not optional: without embeddings the chatbot silently stops matching FAQs and
# sends every question to the model, so a failure here must stop the deploy.
# --delete-orphans: drop rows no longer in faq.yaml, so entries merged away
# during a corpus cleanup stop competing for matches.
python manage.py rebuild_faq_embeddings --delete-orphans --settings=PRODUCTION_SETTINGS_PLACEHOLDER || {
    echo -e "${RED}❌ FAQ embedding failed — aborting deploy${NC}"
    exit 1
}
echo -e "${GREEN}✅ FAQ embeddings rebuilt${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 7: Collect Static Files${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

echo -e "${BLUE}📂 Collecting static files...${NC}"
python manage.py collectstatic --noinput --settings=PRODUCTION_SETTINGS_PLACEHOLDER
echo -e "${GREEN}✅ Static files collected${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 8: Reload Web Application${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

echo -e "${BLUE}🔄 Reloading web app...${NC}"
touch PRODUCTION_WSGI_PLACEHOLDER
echo -e "${GREEN}✅ Web app reloaded${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 9: Disable Maintenance Mode${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

echo -e "${BLUE}🔓 Disabling maintenance mode...${NC}"
python manage.py maintenance_mode off --settings=PRODUCTION_SETTINGS_PLACEHOLDER
echo -e "${GREEN}✅ Site is now live!${NC}"
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ DEPLOYMENT COMPLETE!                                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"

ENDSSH
)

# Replace placeholders and execute
DEPLOY_SCRIPT="${DEPLOY_SCRIPT//PRODUCTION_DIR_PLACEHOLDER/$PRODUCTION_DIR}"
DEPLOY_SCRIPT="${DEPLOY_SCRIPT//PRODUCTION_VENV_PLACEHOLDER/$PRODUCTION_VENV}"
DEPLOY_SCRIPT="${DEPLOY_SCRIPT//PRODUCTION_SETTINGS_PLACEHOLDER/$PRODUCTION_SETTINGS}"
DEPLOY_SCRIPT="${DEPLOY_SCRIPT//PRODUCTION_WSGI_PLACEHOLDER/$PRODUCTION_WSGI}"

ssh ${PRODUCTION_HOST} "${DEPLOY_SCRIPT}"

echo ""
echo -e "${GREEN}✨ Production deployment finished!${NC}"
echo -e "${BLUE}🌐 Visit: https://www.tcsp.ie${NC}"
echo ""
echo -e "${YELLOW}📋 Post-Deployment Checklist:${NC}"
echo "   1. Test login and authentication"
echo "   2. Test booking flow with BOIPA payments"
echo "   3. Test chatbot functionality"
echo "   4. Check admin panels are accessible"
echo "   5. Monitor error logs for 30 minutes"
echo "   6. Verify static files are loading (CSS/JS)"
echo ""
echo -e "${BLUE}📊 Monitor logs with:${NC}"
echo "   ssh ${PRODUCTION_HOST} 'tail -f /var/www/logs/error.log'"
echo ""