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

# Tailwind stylesheet freshness.
#
# static/css/styles.css is a committed artifact, and PythonAnywhere has no Node,
# so it can only be built here. Tailwind emits just the classes it finds when it
# runs, which means a class added to a template since the last build is silently
# missing from the deployed stylesheet — no error, just an unstyled element. The
# chat panel shipped full-width exactly this way.
#
# Rebuild to a temporary file and compare. This never writes to the working tree
# and never commits: a deploy quietly amending a tracked file is worse than one
# that stops and says what to do.
if command -v npx >/dev/null 2>&1 && [ -d node_modules ]; then
    echo -e "${YELLOW}🎨 Checking the Tailwind stylesheet is current${NC}"
    TMP_CSS=$(mktemp -t tcsp_styles)
    if npx tailwindcss -i ./static/src/input.css -o "$TMP_CSS" >/dev/null 2>&1; then
        if ! cmp -s "$TMP_CSS" static/css/styles.css; then
            rm -f "$TMP_CSS"
            echo -e "${RED}❌ static/css/styles.css is out of date${NC}"
            echo -e "${YELLOW}   A class used in a template is missing from the built stylesheet.${NC}"
            echo -e "${YELLOW}   Run:  npm run build:css${NC}"
            echo -e "${YELLOW}   then commit and push static/css/styles.css, and deploy again.${NC}"
            exit 1
        fi
        echo -e "${GREEN}✅ Stylesheet is up to date${NC}"
    else
        # A broken build must not block a deploy of unrelated Python changes.
        echo -e "${YELLOW}⚠️  Could not run Tailwind — skipping the stylesheet check${NC}"
    fi
    rm -f "$TMP_CSS"
else
    echo -e "${YELLOW}⚠️  Node or node_modules missing — skipping the stylesheet check${NC}"
    echo -e "${YELLOW}   Run 'npm install' if you edit templates on this machine.${NC}"
fi
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

# Stash BEFORE enabling maintenance, not after. The mode is stored in the tracked
# file config/maintenance_mode_state.txt, so a stash taken afterwards captures the
# "on" state as a local change and reverts the file — putting the site straight
# back to live. Every deploy before this one therefore migrated against a site
# that was still serving, and left the stash behind, which is where the backlog
# of stashes came from.
echo -e "${BLUE}📦 Stashing local changes...${NC}"
git stash

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

git fetch origin main

# Production carries migration files that were generated here and never committed.
# When one shares a path with a file an incoming commit adds, git refuses to
# overwrite it and the pull aborts — with the site already in maintenance. Move
# any such file aside: git is about to write its own copy of that exact path, and
# the original is kept so nothing is lost. Git refuses even when the contents are
# byte-identical, so this cannot be skipped by comparing first.
MIGRATION_BACKUPS="../prod-migration-backups"
git diff --name-only HEAD origin/main | sort > /tmp/tcsp_incoming.$$
git status --short --untracked-files=all | grep '^??' | sed 's/^?? //' | sort > /tmp/tcsp_untracked.$$
COLLISIONS=$(comm -12 /tmp/tcsp_incoming.$$ /tmp/tcsp_untracked.$$)
rm -f /tmp/tcsp_incoming.$$ /tmp/tcsp_untracked.$$

if [ -n "$COLLISIONS" ]; then
    mkdir -p "$MIGRATION_BACKUPS"
    echo -e "${YELLOW}⚠️  Untracked files in the way of the pull:${NC}"
    echo "$COLLISIONS" | while read -r f; do
        DEST="$MIGRATION_BACKUPS/$(echo "$f" | tr '/' '_').$(date +%Y%m%d-%H%M%S)"
        cp "$f" "$DEST"
        if git show "origin/main:$f" | diff -q - "$f" >/dev/null 2>&1; then
            echo -e "   ${BLUE}$f${NC} (identical to incoming) → $DEST"
        else
            # Worth saying out loud: the copy being replaced was not the same file.
            echo -e "   ${YELLOW}$f (DIFFERS from incoming)${NC} → $DEST"
        fi
        rm -f "$f"
    done
fi

echo -e "${BLUE}⬇️  Pulling latest code...${NC}"
git pull origin main
git log --oneline -1

# Assert maintenance mode rather than assume it. The flag lives in a tracked file,
# so the pull can move it, and everything after this point changes the schema.
python manage.py maintenance_mode on --settings=PRODUCTION_SETTINGS_PLACEHOLDER >/dev/null 2>&1 || true
MAINT_STATE=$(cat config/maintenance_mode_state.txt 2>/dev/null || echo "unknown")
if [ "$MAINT_STATE" != "1" ]; then
    echo -e "${RED}❌ Maintenance mode is '${MAINT_STATE}', not 1 — aborting before the schema changes${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Code updated, maintenance mode confirmed on${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 4: Update Dependencies${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

echo -e "${BLUE}🐍 Installing/updating packages...${NC}"
pip install -r requirements.txt --upgrade --quiet
echo -e "${GREEN}✅ Dependencies updated${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 5: Reconcile Migration Branches${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

# Production's migration history has branches the repo does not, and deliberately
# so — see the "Commit the missing lessons price migration" commit for why they
# are not committed. When a migration arrives from the repo alongside one of
# production's own, the app is left with two leaf nodes and migrate refuses to run
# at all, which would strand the deploy here with the site already down.
#
# Only merge when a conflict is actually detected, and only for the apps that have
# one. Running makemigrations --merge unconditionally is not safe: on a graph with
# no conflicts it falls through to ordinary makemigrations, which could invent
# migrations on production from whatever the models happen to say.
echo -e "${BLUE}🔍 Checking for conflicting migration leaves...${NC}"
CONFLICT_APPS=$(python - <<'PYEOF'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PRODUCTION_SETTINGS_PLACEHOLDER")
django.setup()
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.migrations.loader import MigrationLoader
loader = MigrationLoader(connections[DEFAULT_DB_ALIAS])
print(" ".join(sorted(loader.detect_conflicts())))
PYEOF
)

if [ -n "$CONFLICT_APPS" ]; then
    echo -e "${YELLOW}⚠️  Conflicting leaves in: ${CONFLICT_APPS}${NC}"
    python manage.py makemigrations --merge --noinput $CONFLICT_APPS --settings=PRODUCTION_SETTINGS_PLACEHOLDER || {
        echo -e "${RED}❌ Could not merge — aborting before the schema is touched${NC}"
        exit 1
    }

    # A merge that did not actually resolve the conflict must not reach migrate.
    STILL_CONFLICTING=$(python - <<'PYEOF'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PRODUCTION_SETTINGS_PLACEHOLDER")
django.setup()
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.migrations.loader import MigrationLoader
loader = MigrationLoader(connections[DEFAULT_DB_ALIAS])
print(" ".join(sorted(loader.detect_conflicts())))
PYEOF
)
    if [ -n "$STILL_CONFLICTING" ]; then
        echo -e "${RED}❌ Still conflicting after merge: ${STILL_CONFLICTING} — aborting${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Merge migration created${NC}"
else
    echo -e "${GREEN}✅ No migration conflicts${NC}"
fi
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 6: Run Database Migrations${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

echo -e "${BLUE}💾 Showing what will be applied...${NC}"
python manage.py migrate --plan --settings=PRODUCTION_SETTINGS_PLACEHOLDER 2>/dev/null | grep -A100 "Planned operations" || echo "   (no pending migrations)"
echo -e "${BLUE}💾 Running migrations...${NC}"
python manage.py migrate --settings=PRODUCTION_SETTINGS_PLACEHOLDER
echo -e "${GREEN}✅ Migrations complete${NC}"

# The cache is a database table (see CACHES in base_settings), and the chatbot's
# rate limiter reads it before the view's error handling starts — so a missing
# table is a 500 on every chat message, not a degraded feature. Idempotent, so
# it runs every deploy rather than being a step somebody has to remember once.
echo -e "${BLUE}🗄️  Ensuring cache table exists...${NC}"
python manage.py createcachetable --settings=PRODUCTION_SETTINGS_PLACEHOLDER
echo -e "${GREEN}✅ Cache table ready${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 7: Rebuild FAQ Embeddings${NC}"
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
echo -e "${YELLOW}STEP 8: Collect Static Files${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

echo -e "${BLUE}📂 Collecting static files...${NC}"
python manage.py collectstatic --noinput --settings=PRODUCTION_SETTINGS_PLACEHOLDER
echo -e "${GREEN}✅ Static files collected${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 9: Reload Web Application${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"

echo -e "${BLUE}🔄 Reloading web app...${NC}"
touch PRODUCTION_WSGI_PLACEHOLDER
echo -e "${GREEN}✅ Web app reloaded${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}STEP 10: Disable Maintenance Mode${NC}"
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