# users/management/commands/export_swimlings_sql.py

import os
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Export Swimling table to exported_sql/swimlings.sql using mysqldump'

    def handle(self, *args, **kwargs):
        BASE_DIR = settings.BASE_DIR
        output_path = os.path.join(BASE_DIR, 'exported_sql', 'swimlings.sql')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Local DB credentials from settings
        db = settings.DATABASES['default']
        db_user = db['USER']
        db_password = db['PASSWORD']
        db_name = db['NAME']
        table_name = 'users_swimling'  # full table name: app_label_modelname

        dump_cmd = [
            'mysqldump',
            f'-u{db_user}',
            f'-p{db_password}',
            '--no-tablespaces',
            db_name,
            table_name
        ]

        self.stdout.write(f"📤 Exporting `{table_name}` to {output_path}...")

        try:
            with open(output_path, 'w') as outfile:
                subprocess.run(dump_cmd, stdout=outfile, check=True)
            self.stdout.write(self.style.SUCCESS(f"✅ Exported successfully to {output_path}"))
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"❌ mysqldump failed: {e}"))
