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
# Remember where we were, so the dependency step below can tell whether
# requirements.txt actually changed in this deploy.
PRE_PULL_SHA=$(git rev-parse HEAD)
git pull origin main
git log --oneline -1

echo '🐍 Activating virtual environment...'
source DEV_VENV_PLACEHOLDER/bin/activate

# Dev used to pull code but never touch the venv, so a requirements.txt change
# deployed as a silent no-op: the files arrived, the packages did not, and dev
# quietly ran a different dependency set from the one the repo pins. Mirrors
# STEP 4 of deploy-to-production.sh, in the same position — after the pull, so
# migrate below runs against the packages this commit actually asks for.
#
# Only install when there is something to install. requirements.txt is pinned
# with == throughout, so a plain `pip install -r` already installs the exact
# pinned version of anything whose installed version no longer matches, and skips
# the rest in seconds. `--upgrade` added nothing on top of that: it forced pip to
# re-resolve and re-download all 200+ pins on every deploy, which is minutes of
# CPU on a shared host — long enough for the host to kill the run part-way and
# leave a package half-installed, as happened on production on 2026-09-19.
#
# The pip check also repairs a venv left broken by an earlier interrupted run,
# even when requirements.txt itself is unchanged.
NEEDS_INSTALL=""
if ! git diff --quiet "$PRE_PULL_SHA" HEAD -- requirements.txt; then
    NEEDS_INSTALL="requirements.txt changed in this pull"
elif ! pip check >/dev/null 2>&1; then
    NEEDS_INSTALL="the venv has broken or missing packages"
fi

if [ -n "$NEEDS_INSTALL" ]; then
    echo "📦 Installing because: ${NEEDS_INSTALL}"
    git diff --stat "$PRE_PULL_SHA" HEAD -- requirements.txt || true
    pip install -r requirements.txt
else
    echo '📦 requirements.txt unchanged and venv intact — nothing to install'
fi

# Verify the environment before anything touches the database. An interrupted pip
# leaves a package half-removed, and that otherwise surfaces much later as an
# unbootable site rather than here as a failed deploy step.
echo '🔎 Verifying the environment...'
python -c "import django; print('   Django ' + django.get_version())" || {
    echo '❌ Django cannot be imported — the venv is broken'
    echo '   Repair with: pip install -r requirements.txt'
    exit 1
}
pip check || {
    echo '❌ pip reports broken requirements — aborting before the schema changes'
    echo '   Repair with: pip install -r requirements.txt'
    exit 1
}

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
REMOTE_PID="dev-deploy-${STAMP}.pid"
SSH_OPTS="-o ServerAliveInterval=30 -o ServerAliveCountMax=6"

# Exit code the follower uses for "the deploy process is gone but never wrote a
# status file" — i.e. it was killed rather than having failed. Distinct from any
# exit code the deploy itself can produce.
VANISHED_EXIT=97

echo "📤 Sending the deploy script to the server..."
printf '%s\n' "$DEPLOY_SCRIPT" | ssh $SSH_OPTS ${DEV_HOST} "cat > ~/${REMOTE_SCRIPT}"

echo "▶️  Launching it detached (survives a dropped connection)..."
# The PID file is what lets the follower tell "still working" from "killed". A
# status file only ever appears if the deploy reached the end of its own shell;
# when the host kills the process outright, nothing is written and the follower
# would otherwise wait on a file that is never coming.
ssh $SSH_OPTS ${DEV_HOST} "cd ~ && setsid nohup bash -c 'echo \$\$ > ~/${REMOTE_PID}; bash ~/${REMOTE_SCRIPT} > ~/${REMOTE_LOG} 2>&1; echo \$? > ~/${REMOTE_STATUS}' < /dev/null > /dev/null 2>&1 &"

echo "   If this terminal dies, the deploy continues. Re-attach with:"
echo "   ssh ${DEV_HOST} 'tail -f ~/${REMOTE_LOG}'"
echo ""

# Watching the PID as well as the status file is what stops this hanging forever.
# On 2026-09-19 the production deploy was killed during its dependency step and
# the equivalent loop there waited on a status file that no longer had anything
# to write it.
set +e
ssh $SSH_OPTS ${DEV_HOST} "
    while [ ! -f ~/${REMOTE_LOG} ]; do sleep 1; done
    tail -n +1 -f ~/${REMOTE_LOG} &
    TAIL_PID=\$!
    DEPLOY_PID=\$(cat ~/${REMOTE_PID} 2>/dev/null)
    while [ ! -f ~/${REMOTE_STATUS} ]; do
        if [ -n \"\$DEPLOY_PID\" ] && ! kill -0 \"\$DEPLOY_PID\" 2>/dev/null; then
            # The process may have exited a moment ago and still be writing its
            # status file, so re-check before calling it a kill.
            sleep 3
            [ -f ~/${REMOTE_STATUS} ] && break
            sleep 2  # let tail flush whatever the deploy managed to log
            kill \$TAIL_PID 2>/dev/null
            exit ${VANISHED_EXIT}
        fi
        sleep 2
    done
    sleep 2  # let tail flush the last lines before it is killed
    kill \$TAIL_PID 2>/dev/null
    exit \$(cat ~/${REMOTE_STATUS})
"
DEPLOY_STATUS=$?
set -e

# Tidy the run script and PID file; keep the log, which is the record of what happened.
ssh $SSH_OPTS ${DEV_HOST} "rm -f ~/${REMOTE_SCRIPT} ~/${REMOTE_PID}; ls -1t ~/dev-deploy-*.log 2>/dev/null | tail -n +11 | xargs -r rm --" || true

if [ "$DEPLOY_STATUS" -eq "$VANISHED_EXIT" ]; then
    echo ""
    echo "❌ The dev deploy process was killed, not failed"
    echo "   The host killed it part-way through, so it never wrote an exit code."
    echo "   The last lines of the log above are the last thing it actually did."
    echo ""
    echo "   The venv may hold a half-installed package. Check with:"
    echo "   ssh ${DEV_HOST} 'cd ~/${DEV_DIR} && ${DEV_VENV}/bin/pip check'"
    echo "   Repair with: ssh ${DEV_HOST} 'cd ~/${DEV_DIR} && ${DEV_VENV}/bin/pip install -r requirements.txt'"
    echo ""
    echo "   Full log: ssh ${DEV_HOST} 'less ~/${REMOTE_LOG}'"
    exit "$DEPLOY_STATUS"
fi

if [ "$DEPLOY_STATUS" -ne 0 ]; then
    echo ""
    echo "❌ Dev deployment failed (exit ${DEPLOY_STATUS})"
    echo "   Full log: ssh ${DEV_HOST} 'less ~/${REMOTE_LOG}'"
    exit "$DEPLOY_STATUS"
fi

echo ""
echo "✨ Your dev server has been updated!"
echo "🌐 Visit: https://dev-morganmck.eu.pythonanywhere.com"
