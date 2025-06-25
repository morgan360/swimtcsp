import os
import subprocess
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Export Program, Category, and Product tables to lessons.sql'

    def handle(self, *args, **options):
        base_dir = settings.BASE_DIR
        output_file = os.path.join(base_dir, 'exported_sql', 'lessons.sql')

        db = settings.DATABASES['default']
        user = db['USER']
        password = db['PASSWORD']
        host = db['HOST']
        name = db['NAME']

        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        tables = ['lessons_program', 'lessons_category', 'lessons_product']

        cmd = [
            'mysqldump',
            f'-u{user}',
            f'-p{password}',
            f'-h{host}',
            '--no-tablespaces',
            name,
            *tables
        ]

        self.stdout.write(f"📤 Exporting to {output_file}...")

        try:
            with open(output_file, 'wb') as f:
                subprocess.run(cmd, check=True, stdout=f)
            self.stdout.write(self.style.SUCCESS("✅ Export successful."))
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"❌ Export failed: {e}"))
