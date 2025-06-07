import os
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Import users.sql into the remote database on PythonAnywhere'

    def handle(self, *args, **kwargs):
        BASE_DIR = settings.BASE_DIR
        sql_file_path = os.path.join(BASE_DIR, 'import_sql', 'users.sql')

        # Update these with your actual PythonAnywhere DB credentials
        db_user = 'morganmck'
        db_password = 'Mongo@8899'
        db_host = 'morganmck.mysql.pythonanywhere-services.com'
        db_name = 'morganmck$swimtcsp'

        if not os.path.exists(sql_file_path):
            self.stderr.write(self.style.ERROR(f"❌ SQL file not found: {sql_file_path}"))
            return

        import_cmd = [
            'mysql',
            f'-u{db_user}',
            f'-p{db_password}',
            f'-h{db_host}',
            db_name
        ]

        self.stdout.write(f"📥 Importing `{sql_file_path}` into `{db_name}`...")

        try:
            with open(sql_file_path, 'r') as sql_file:
                subprocess.run(import_cmd, stdin=sql_file, check=True)
            self.stdout.write(self.style.SUCCESS(f"✅ Imported successfully into `{db_name}`"))
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"❌ Import failed: {e}"))
