#!/bin/bash
# Deployment script for PythonAnywhere dev server
# Usage: ./deploy-to-dev.sh

set -e  # Exit on error

# Keep the Mac awake for the whole deploy — see deploy-to-production.sh for the
# full story. Shorter here (no database backup), but pip --upgrade and
# collectstatic are still enough to let an idle machine sleep and cut the
# connection mid-migration.
if [ "$(uname)" = "Darwin" ] && [ -z "$TCSP_CAFFEINATED" ] && command -v caffeinate >/dev/null 2>&1; then
    export TCSP_CAFFEINATED=1
    exec caffeinate -i "$0" "$@"
fi

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

# The cache is a database table (see CACHES in base_settings), and the chatbot's
# rate limiter reads it before the view's error handling starts — so a missing
# table is a 500 on every chat message, not a degraded feature. Idempotent, so
# it runs every deploy rather than being a step somebody has to remember once.
echo '🗄️  Ensuring cache table exists...'
python manage.py createcachetable --settings=DEV_SETTINGS_PLACEHOLDER

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

# Run detached on the server and follow the log from here, as production does.
# Dev has no maintenance mode, so a dropped connection cannot strand the site —
# but it can still kill the run part-way through migrate or collectstatic and
# leave dev in a state nobody chose. Detaching costs nothing and removes that.
STAMP=$(date +%Y%m%d-%H%M%S)
REMOTE_SCRIPT="dev-deploy-run-${STAMP}.sh"
REMOTE_LOG="dev-deploy-${STAMP}.log"
REMOTE_STATUS="dev-deploy-${STAMP}.status"
SSH_OPTS="-o ServerAliveInterval=30 -o ServerAliveCountMax=6"

echo "📤 Sending the deploy script to the server..."
printf '%s\n' "$DEPLOY_SCRIPT" | ssh $SSH_OPTS ${DEV_HOST} "cat > ~/${REMOTE_SCRIPT}"

echo "▶️  Launching it detached (survives a dropped connection)..."
ssh $SSH_OPTS ${DEV_HOST} "cd ~ && setsid nohup bash -c 'bash ~/${REMOTE_SCRIPT} > ~/${REMOTE_LOG} 2>&1; echo \$? > ~/${REMOTE_STATUS}' < /dev/null > /dev/null 2>&1 &"

echo "   If this terminal dies, the deploy continues. Re-attach with:"
echo "   ssh ${DEV_HOST} 'tail -f ~/${REMOTE_LOG}'"
echo ""

set +e
ssh $SSH_OPTS ${DEV_HOST} "
    while [ ! -f ~/${REMOTE_LOG} ]; do sleep 1; done
    tail -n +1 -f ~/${REMOTE_LOG} &
    TAIL_PID=\$!
    while [ ! -f ~/${REMOTE_STATUS} ]; do sleep 2; done
    sleep 2  # let tail flush the last lines before it is killed
    kill \$TAIL_PID 2>/dev/null
    exit \$(cat ~/${REMOTE_STATUS})
"
DEPLOY_STATUS=$?
set -e

# Tidy the run script; keep the log, which is the record of what happened.
ssh $SSH_OPTS ${DEV_HOST} "rm -f ~/${REMOTE_SCRIPT}; ls -1t ~/dev-deploy-*.log 2>/dev/null | tail -n +11 | xargs -r rm --" || true

if [ "$DEPLOY_STATUS" -ne 0 ]; then
    echo ""
    echo "❌ Dev deployment failed (exit ${DEPLOY_STATUS})"
    echo "   Full log: ssh ${DEV_HOST} 'less ~/${REMOTE_LOG}'"
    exit "$DEPLOY_STATUS"
fi

echo ""
echo "✨ Your dev server has been updated!"
echo "🌐 Visit: https://dev-morganmck.eu.pythonanywhere.com"
