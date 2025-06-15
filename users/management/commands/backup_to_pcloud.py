import subprocess
from datetime import datetime
import os
import requests
from django.core.management.base import BaseCommand
from decouple import config


class Command(BaseCommand):
    help = "Backs up remote MySQL DB and uploads to pCloud (EU)"

    def handle(self, *args, **options):
        # Read env variables
        db_host = config('REMOTE_TCSP_DB_HOST')
        db_user = config('REMOTE_TCSP_DB_USER')
        db_name = config('REMOTE_TCSP_DB_NAME')
        db_password = config('REMOTE_TCSP_DB_PASSWORD')
        pcloud_email = config('PCLOUD_EMAIL')
        pcloud_password = config('PCLOUD_PASSWORD')
        folder_id = config('PCLOUD_FOLDER_ID', default='0')

        # File paths
        today = datetime.now().strftime('%Y-%m-%d')
        backup_filename = f'db_backup_{today}.sql'
        backup_path = os.path.join('/tmp', backup_filename)

        self.stdout.write(f"📦 Dumping database to {backup_path}...")
        try:
            # Run mysqldump securely
            dump_cmd = [
                'mysqldump',
                '-h', db_host,
                '-u', db_user,
                f'-p{db_password}',
                '--single-transaction',
                '--skip-lock-tables',
                '--skip-add-locks',
                '--no-tablespaces',  # ✅ This line is key
                db_name
            ]
            with open(backup_path, 'w') as f:
                subprocess.run(dump_cmd, stdout=f, check=True)
        except subprocess.CalledProcessError:
            self.stderr.write("❌ Failed to dump database.")
            return

        # Authenticate with pCloud EU
        self.stdout.write("🔐 Logging into pCloud...")
        login_resp = requests.get('https://eapi.pcloud.com/login', params={
            'getauth': 1,
            'username': pcloud_email,
            'password': pcloud_password
        }).json()

        if not login_resp.get("auth"):
            self.stderr.write("❌ pCloud login failed.")
            return

        auth_token = login_resp['auth']

        # Upload the file
        self.stdout.write(f"☁️ Uploading {backup_filename} to pCloud...")
        with open(backup_path, 'rb') as f:
            upload_resp = requests.post("https://eapi.pcloud.com/uploadfile", params={
                'auth': auth_token,
                'folderid': folder_id
            }, files={'file': (backup_filename, f)})

        if upload_resp.status_code == 200:
            self.stdout.write("✅ Backup uploaded successfully to pCloud.")
        else:
            self.stderr.write(f"❌ Upload failed: {upload_resp.text}")
