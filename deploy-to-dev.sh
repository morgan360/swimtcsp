#!/bin/bash
# Deployment script for PythonAnywhere dev server
# Usage: ./deploy-to-dev.sh

set -e  # Exit on error

DEV_HOST="ssh.eu.pythonanywhere.com"
DEV_DIR="dev-swimtcsp"
DEV_VENV="../.virtualenvs/dev-swimtcsp"
DEV_SETTINGS="config.development_settings"
DEV_WSGI="/var/www/dev-morganmck_eu_pythonanywhere_com_wsgi.py"

echo "🚀 Starting deployment to dev-morganmck.eu.pythonanywhere.com..."

# Sent as a quoted heredoc so the remote shell evaluates $(...) and $$, rather
# than this one expanding them before the command is sent.
DEPLOY_SCRIPT=$(cat << 'ENDSSH'
set -e

cd DEV_DIR_PLACEHOLDER

echo '📦 Stashing local changes...'
git stash

echo '🔍 Checking for untracked files in the way of the pull...'
git fetch origin main

# The dev server carries migration files generated here and never committed. When
# one shares a path with a file an incoming commit adds, git refuses to overwrite
# it and the pull aborts. Move any such file aside: git is about to write its own
# copy of that exact path, and the original is kept so nothing is lost. Git
# refuses even when the contents are byte-identical, so comparing first would not
# let us skip this.
MIGRATION_BACKUPS="../dev-migration-backups"
git diff --name-only HEAD origin/main | sort > /tmp/tcsp_dev_incoming.$$
git status --short --untracked-files=all | grep '^??' | sed 's/^?? //' | sort > /tmp/tcsp_dev_untracked.$$
COLLISIONS=$(comm -12 /tmp/tcsp_dev_incoming.$$ /tmp/tcsp_dev_untracked.$$)
rm -f /tmp/tcsp_dev_incoming.$$ /tmp/tcsp_dev_untracked.$$

if [ -n "$COLLISIONS" ]; then
    mkdir -p "$MIGRATION_BACKUPS"
    echo '⚠️  Moving these aside first:'
    echo "$COLLISIONS" | while read -r f; do
        DEST="$MIGRATION_BACKUPS/$(echo "$f" | tr '/' '_').$(date +%Y%m%d-%H%M%S)"
        cp "$f" "$DEST"
        if git show "origin/main:$f" | diff -q - "$f" >/dev/null 2>&1; then
            echo "   $f (identical to incoming) → $DEST"
        else
            # Worth saying out loud: the copy being replaced was not the same file.
            echo "   $f (DIFFERS from incoming) → $DEST"
        fi
        rm -f "$f"
    done
else
    echo '   none'
fi

echo '⬇️  Pulling latest code from GitHub...'
git pull origin main
git log --oneline -1

echo '🐍 Activating virtual environment...'
source DEV_VENV_PLACEHOLDER/bin/activate

# Dev has migration branches the repo does not, the same way production does. A
# migration arriving from the repo alongside one of dev's own leaves two leaf
# nodes, and migrate then refuses to run at all. Merge only when a conflict is
# actually detected, and only for the apps that have one: running
# makemigrations --merge on a clean graph falls through to ordinary
# makemigrations, which could invent migrations from whatever the models say.
echo '🔍 Checking for conflicting migration leaves...'
CONFLICT_APPS=$(python - <<'PYEOF'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DEV_SETTINGS_PLACEHOLDER")
django.setup()
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.migrations.loader import MigrationLoader
loader = MigrationLoader(connections[DEFAULT_DB_ALIAS])
print(" ".join(sorted(loader.detect_conflicts())))
PYEOF
)

if [ -n "$CONFLICT_APPS" ]; then
    echo "⚠️  Conflicting leaves in: $CONFLICT_APPS"
    python manage.py makemigrations --merge --noinput $CONFLICT_APPS --settings=DEV_SETTINGS_PLACEHOLDER || {
        echo '❌ Could not merge — aborting before the schema is touched'
        exit 1
    }
    STILL_CONFLICTING=$(python - <<'PYEOF'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DEV_SETTINGS_PLACEHOLDER")
django.setup()
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.migrations.loader import MigrationLoader
loader = MigrationLoader(connections[DEFAULT_DB_ALIAS])
print(" ".join(sorted(loader.detect_conflicts())))
PYEOF
)
    if [ -n "$STILL_CONFLICTING" ]; then
        echo "❌ Still conflicting after merge: $STILL_CONFLICTING — aborting"
        exit 1
    fi
    echo '✅ Merge migration created'
else
    echo '   none'
fi

echo '💾 Running database migrations...'
python manage.py migrate --settings=DEV_SETTINGS_PLACEHOLDER

echo '📂 Collecting static files...'
python manage.py collectstatic --noinput --settings=DEV_SETTINGS_PLACEHOLDER

echo '🔄 Reloading web app...'
touch DEV_WSGI_PLACEHOLDER

echo '✅ Deployment complete!'
ENDSSH
)

DEPLOY_SCRIPT="${DEPLOY_SCRIPT//DEV_DIR_PLACEHOLDER/$DEV_DIR}"
DEPLOY_SCRIPT="${DEPLOY_SCRIPT//DEV_VENV_PLACEHOLDER/$DEV_VENV}"
DEPLOY_SCRIPT="${DEPLOY_SCRIPT//DEV_SETTINGS_PLACEHOLDER/$DEV_SETTINGS}"
DEPLOY_SCRIPT="${DEPLOY_SCRIPT//DEV_WSGI_PLACEHOLDER/$DEV_WSGI}"

ssh ${DEV_HOST} "${DEPLOY_SCRIPT}"

echo ""
echo "✨ Your dev server has been updated!"
echo "🌐 Visit: https://dev-morganmck.eu.pythonanywhere.com"
