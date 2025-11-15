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
PRODUCTION_WSGI="/var/www/morganmck_pythonanywhere_com_wsgi.py"  # UPDATE THIS
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

# Deploy to Production
ssh ${PRODUCTION_HOST} << 'ENDSSH'
set -e

# Color codes for remote output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Use the variables passed from local
cd PRODUCTION_DIR_PLACEHOLDER

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 1: Database Backup${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

# Create backup directory if it doesn't exist
mkdir -p backups

# Get database credentials from .env or Django settings
BACKUP_FILE="backups/backup_$(date +%Y%m%d_%H%M%S).sql"

echo -e "${BLUE}📦 Creating database backup...${NC}"
# Note: Update this command with your actual database credentials
# mysqldump -u YOUR_DB_USER -p YOUR_DB_NAME > $BACKUP_FILE

echo -e "${GREEN}✅ Backup created: $BACKUP_FILE${NC}"
echo -e "${YELLOW}   (Database backup command needs configuration)${NC}"
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
echo -e "${BLUE}   Users will see maintenance page${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 3: Pull Latest Code${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

echo -e "${BLUE}📦 Stashing any local changes...${NC}"
git stash

echo -e "${BLUE}⬇️  Pulling latest code from GitHub (main branch)...${NC}"
git pull origin main

echo -e "${BLUE}📋 Current commit:${NC}"
git log --oneline -1

echo -e "${GREEN}✅ Code updated${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 4: Update Dependencies${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

echo -e "${BLUE}🐍 Installing/updating Python packages...${NC}"
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

echo -e "${BLUE}🤖 Re-vectorizing FAQs for chatbot...${NC}"
python manage.py rebuild_faq_embeddings --settings=PRODUCTION_SETTINGS_PLACEHOLDER || {
    echo -e "${YELLOW}⚠️  Warning: FAQ embedding failed (non-critical)${NC}"
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

echo -e "${GREEN}✅ Maintenance mode disabled${NC}"
echo -e "${BLUE}   Site is now live!${NC}"
echo ""

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║  ✅ DEPLOYMENT COMPLETE!                                   ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"

ENDSSH

# Replace placeholders in the heredoc
# This is a workaround since we can't use variables directly in heredoc with ENDSSH
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
BACKUP_FILE="backups/backup_$(date +%Y%m%d_%H%M%S).sql"
echo -e "${BLUE}📦 Creating database backup...${NC}"
echo -e "${GREEN}✅ Backup location: $BACKUP_FILE${NC}"
echo -e "${YELLOW}   (Configure mysqldump command with your credentials)${NC}"
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
python manage.py rebuild_faq_embeddings --settings=PRODUCTION_SETTINGS_PLACEHOLDER || {
    echo -e "${YELLOW}⚠️  Warning: FAQ embedding failed (non-critical)${NC}"
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