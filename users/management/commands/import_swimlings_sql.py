# users/management/commands/import_swimlings_sql.py

import os
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Import swimlings.sql into the connected MySQL database'

    def handle(self, *args, **options):
        base_dir = settings.BASE_DIR
        sql_file_path = os.path.join(base_dir, 'exported_sql', 'swimlings.sql')

        if not os.path.exists(sql_file_path):
            self.stderr.write(self.style.ERROR(f"❌ SQL file not found: {sql_file_path}"))
            return

        # Get DB credentials from Django settings
        db = settings.DATABASES['default']
        user = db['USER']
        password = db['PASSWORD']
        host = db['HOST']
        name = db['NAME']

        cmd = [
            'mysql',
            f'-u{user}',
            f'-p{password}',
            f'-h{host}',
            name
        ]

        self.stdout.write(self.style.WARNING(f"📥 Importing {sql_file_path} into `{name}`..."))

        try:
            with open(sql_file_path, 'rb') as sql_file:
                subprocess.run(cmd, stdin=sql_file, check=True)
            self.stdout.write(self.style.SUCCESS("✅ Import complete."))
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"❌ MySQL import failed: {e}"))
