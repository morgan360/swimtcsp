import pymysql
from django.core.management.base import BaseCommand
from users.models import Swimling, User
from django.db import connection, transaction

class Command(BaseCommand):
    help = 'Import Swimlings from remote WordPress DB into local Django DB preserving original IDs'

    def handle(self, *args, **kwargs):
        connection_details = {
            "host": 'tcsp.ie',
            "port": 3306,
            "user": 't567715',
            "password": '0bjs8Pz55Q',
            "database": 't567715_wp_tcsp',
            "charset": 'utf8mb4',
            "cursorclass": pymysql.cursors.DictCursor
        }

        query = """
        SELECT id AS wp_id,
               guardian_id,
               first_name,
               last_name,
               notes
        FROM t567715_wp_tcsp.mor_student_details
        """

        try:
            self.stdout.write("🔌 Connecting to remote database...")
            remote_conn = pymysql.connect(**connection_details)
        except pymysql.MySQLError as e:
            self.stderr.write(f"❌ Connection failed: {e}")
            return

        try:
            with remote_conn.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

            created, skipped = 0, 0
            with transaction.atomic():
                for row in rows:
                    try:
                        guardian = User.objects.get(id=row['guardian_id'])
                    except User.DoesNotExist:
                        skipped += 1
                        continue

                    swimling_id = int(row['wp_id'])

                    # Delete if exists to avoid duplicate PK error
                    Swimling.objects.filter(id=swimling_id).delete()

                    Swimling.objects.create(
                        id=swimling_id,
                        guardian=guardian,
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        notes=row['notes']
                    )
                    created += 1

                with connection.cursor() as cursor:
                    cursor.execute("SELECT MAX(id) + 1 FROM users_swimling")
                    next_id = cursor.fetchone()[0] or 1  # fallback to 1 if table is empty
                    cursor.execute(f"ALTER TABLE users_swimling AUTO_INCREMENT = {next_id}")

            self.stdout.write(self.style.SUCCESS(f"✅ Imported {created} Swimlings"))
            self.stdout.write(self.style.WARNING(f"⚠️ Skipped {skipped} due to missing guardian"))

        finally:
            remote_conn.close()
