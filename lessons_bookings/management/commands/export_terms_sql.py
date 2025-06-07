# lessons_bookings/management/commands/export_terms_sql.py

import os
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Export lessons_bookings_term table to import_sql/mor_terms.sql using mysqldump'

    def handle(self, *args, **kwargs):
        BASE_DIR = settings.BASE_DIR
        output_path = os.path.join(BASE_DIR, 'exported_sql', 'mor_terms.sql')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Local DB credentials for mysqldump
        db_user = 'swimuser'
        db_password = 'StrongPass!2025'
        db_name = 'swimtcsp'
        table_name = 'lessons_bookings_term'

        dump_cmd = [
            'mysqldump',
            f'-u{db_user}',
            f'-p{db_password}',  # warning: exposes password if viewed via ps
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

