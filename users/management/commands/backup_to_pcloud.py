"""Nightly off-site copy of the production database to pCloud (EU), kept 30 days.

Runs as a PythonAnywhere scheduled task at 04:00. Until November 2026 this
dumped the old WordPress database, which no longer answers, so the live booking
site had no off-site backup at all. It now dumps the site's own database
(``settings.DATABASES['default']``), gzipped, into its own pCloud folder.

Signing in: the pCloud account has two-factor on, so a password login from the
server is refused ("Please provide 'code'"). ``PCLOUD_AUTH`` holds a long-lived
token made once on a trusted computer instead::

    python manage.py backup_to_pcloud --make-token     # prints a token for .env

The token stops working after a year (or two months unused); the nightly run
then fails loudly and the daily error digest shows it. Make a new one.

Keeping: after a successful upload, backups older than ``KEEP_DAYS`` are
deleted, as promised to Esther and Brian with the retention policy — erased
customer details must not live on in old copies. Only files named exactly like
these backups are touched, the newest ``MIN_KEEP`` are always kept, and nothing
is deleted on a night the backup failed. pCloud moves deleted files to its
Trash, which it empties on its own schedule.

Usage
-----
    python manage.py backup_to_pcloud                         # back up, then prune
    python manage.py backup_to_pcloud --prune-only --dry-run  # list what would go
"""
import getpass
import gzip
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta

import requests
from decouple import config
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

API = "https://eapi.pcloud.com"
FOLDER = "/TCSP database backups"
KEEP_DAYS = 30
MIN_KEEP = 7
TOKEN_LIFETIME = 365 * 24 * 3600
BACKUP_NAME = re.compile(r"^db_backup_(\d{2}-[A-Za-z]{3}-\d{4})\.sql(\.gz)?$")


def backup_date(name):
    """The date in a backup's file name, or None if it is not one of ours."""
    match = BACKUP_NAME.match(name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%d-%b-%Y").date()
    except ValueError:
        return None


def backups_to_delete(files, today, keep_days=KEEP_DAYS, min_keep=MIN_KEEP):
    """Pick the expired backups from a pCloud folder listing.

    ``files`` are pCloud metadata dicts. Returns (file, date) pairs, oldest first.
    """
    ours = []
    for item in files:
        if item.get("isfolder"):
            continue
        day = backup_date(item.get("name", ""))
        if day is not None:
            ours.append((item, day))
    ours.sort(key=lambda pair: pair[1], reverse=True)  # newest first
    cutoff = today - timedelta(days=keep_days)
    expired = [pair for pair in ours[min_keep:] if pair[1] < cutoff]
    return sorted(expired, key=lambda pair: pair[1])


class PCloudError(Exception):
    pass


def call(method, **params):
    response = requests.get(f"{API}/{method}", params=params, timeout=60)
    data = response.json()
    if data.get("result") != 0:
        raise PCloudError(f"{method}: {data.get('error') or data}")
    return data


class Command(BaseCommand):
    help = "Back up the production database to pCloud and delete backups older than 30 days."

    def add_arguments(self, parser):
        parser.add_argument("--prune-only", action="store_true", help="Skip the backup; only delete expired ones.")
        parser.add_argument("--dry-run", action="store_true", help="List what would be deleted; delete nothing.")
        parser.add_argument("--make-token", action="store_true",
                            help="Sign in (on a trusted computer) and print a PCLOUD_AUTH token.")

    def handle(self, *args, **options):
        if options["make_token"]:
            return self.make_token()

        auth = config("PCLOUD_AUTH", default="")
        if not auth:
            raise CommandError("PCLOUD_AUTH is not set. Run --make-token on a trusted computer.")

        try:
            folder_id = call("createfolderifnotexists", auth=auth, path=FOLDER)["metadata"]["folderid"]
        except (PCloudError, requests.RequestException, ValueError) as exc:
            # Fails here when the token has expired. Exit non-zero so the
            # scheduled-task log, and with it the daily digest, shows it.
            raise CommandError(f"pCloud refused the token ({exc}). Make a new one with --make-token.")

        if not options["prune_only"] and not self.backup(auth, folder_id):
            raise CommandError("Backup failed, so no old backups were deleted either.")

        try:
            self.prune(auth, folder_id, dry_run=options["dry_run"])
        except (PCloudError, requests.RequestException, ValueError) as exc:
            raise CommandError(f"Backup uploaded, but old ones could not be cleared: {exc}")

    def make_token(self):
        email = config("PCLOUD_EMAIL", default="") or input("pCloud email: ")
        password = config("PCLOUD_PASSWORD", default="") or getpass.getpass("pCloud password: ")
        params = {"getauth": 1, "username": email, "password": password,
                  "authexpire": TOKEN_LIFETIME, "authinactiveexpire": TOKEN_LIFETIME}
        data = requests.get(f"{API}/login", params=params, timeout=60).json()
        if data.get("result") != 0 and data.get("token") and sys.stdin.isatty():
            # Two-factor asked for a code: finish with it.
            code = input("pCloud two-factor code: ")
            data = requests.get(f"{API}/tfa_login", params={
                "token": data["token"], "code": code, "getauth": 1,
                "authexpire": TOKEN_LIFETIME, "authinactiveexpire": TOKEN_LIFETIME}, timeout=60).json()
        if data.get("result") != 0 or not data.get("auth"):
            raise CommandError(f"pCloud sign-in failed: {data.get('error') or data}")
        self.stdout.write("Add this line to the server's .env (keep it secret; it opens the whole pCloud account):")
        self.stdout.write(f"PCLOUD_AUTH={data['auth']}")

    def backup(self, auth, folder_id):
        db = settings.DATABASES["default"]
        name = f"db_backup_{datetime.now():%d-%b-%Y}.sql.gz"
        sql_path = os.path.join("/tmp", name[:-3])
        gz_path = os.path.join("/tmp", name)

        dump_cmd = ["mysqldump", "-h", db["HOST"], "-u", db["USER"],
                    "--single-transaction", "--skip-lock-tables", "--skip-add-locks", "--no-tablespaces"]
        if db.get("PORT"):
            dump_cmd += ["-P", str(db["PORT"])]
        dump_cmd.append(db["NAME"])
        # Password through the environment, not the command line, where any
        # process listing on the shared server would show it.
        env = {**os.environ, "MYSQL_PWD": db["PASSWORD"]}

        self.stdout.write(f"📦 Dumping {db['NAME']}...")
        try:
            try:
                with open(sql_path, "w") as f:
                    subprocess.run(dump_cmd, stdout=f, check=True, env=env)
            except (subprocess.CalledProcessError, OSError) as exc:
                self.stderr.write(f"❌ Failed to dump database: {exc}")
                return False
            # An empty dump is how the old version failed unnoticed for months.
            if os.path.getsize(sql_path) < 100_000:
                self.stderr.write(f"❌ Dump is only {os.path.getsize(sql_path)} bytes; not uploading it.")
                return False
            with open(sql_path, "rb") as src, gzip.open(gz_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

            self.stdout.write(f"☁️ Uploading {name} ({os.path.getsize(gz_path) // 1024} KB) to pCloud...")
            try:
                with open(gz_path, "rb") as f:
                    response = requests.post(f"{API}/uploadfile", params={"auth": auth, "folderid": folder_id},
                                             files={"file": (name, f)}, timeout=600)
                data = response.json()
            except (requests.RequestException, ValueError) as exc:
                self.stderr.write(f"❌ Upload failed: {exc}")
                return False
            # pCloud answers 200 even when it refuses, so check its own result code.
            if data.get("result") != 0:
                self.stderr.write(f"❌ Upload failed: {data.get('error') or data}")
                return False
            self.stdout.write("✅ Backup uploaded to pCloud.")
            return True
        finally:
            # The dump is the whole customer database; do not leave it in /tmp.
            for path in (sql_path, gz_path):
                if os.path.exists(path):
                    os.remove(path)

    def prune(self, auth, folder_id, dry_run):
        listing = call("listfolder", auth=auth, folderid=folder_id)
        files = listing.get("metadata", {}).get("contents", [])
        expired = backups_to_delete(files, date.today())
        if not expired:
            self.stdout.write(f"🧹 No backups older than {KEEP_DAYS} days.")
            return
        for item, day in expired:
            if dry_run:
                self.stdout.write(f"   would delete {item['name']}")
                continue
            call("deletefile", auth=auth, fileid=item["fileid"])
            self.stdout.write(f"   deleted {item['name']}")
        verb = "Would delete" if dry_run else "Deleted"
        self.stdout.write(f"🧹 {verb} {len(expired)} backup(s) older than {KEEP_DAYS} days "
                          f"(oldest {expired[0][1]:%d %b %Y}, newest {expired[-1][1]:%d %b %Y}).")
