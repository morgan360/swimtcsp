import os
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Export the custom User table to exported_sql/users.sql using mysqldump'

    def handle(self, *args, **kwargs):
        BASE_DIR = settings.BASE_DIR
        output_dir = os.path.join(BASE_DIR, 'exported_sql')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'users.sql')

        db_user = 'swimuser'            # Update if different
        db_password = 'StrongPass!2025' # WARNING: avoid committing passwords!
        db_name = 'swimtcsp'
        table_name = 'users_user'       # Django uses appname_modelname format

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
            with open(output_path, 'w') as f:
                subprocess.run(dump_cmd, stdout=f, check=True)
            self.stdout.write(self.style.SUCCESS(f"✅ Exported successfully to {output_path}"))
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"❌ Export failed: {e}"))
