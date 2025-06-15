import pymysql
from decouple import config
from django.core.management.base import BaseCommand
from users.models import Swimling, User
from django.db import connection, transaction

class Command(BaseCommand):
    help = 'Import Swimlings from remote WordPress DB into local Django DB, preserving original IDs and resetting AUTO_INCREMENT'

    def handle(self, *args, **kwargs):
        connection_details = {
            "host": config("REMOTE_TCSP_DB_HOST"),
            "port": int(config("REMOTE_TCSP_DB_PORT", default=3306)),
            "user": config("REMOTE_TCSP_DB_USER"),
            "password": config("REMOTE_TCSP_DB_PASSWORD"),
            "database": config("REMOTE_TCSP_DB_NAME"),
            "charset": config("REMOTE_TCSP_DB_CHARSET", default="utf8mb4"),
            "cursorclass": pymysql.cursors.DictCursor
        }

        query = """
        SELECT id AS wp_id,
               guardian_id,
               first_name,
               last_name,
               notes
        FROM mor_student_details
        """

        try:
            self.stdout.write("🔌 Connecting to remote database...")
            remote_conn = pymysql.connect(**connection_details)
        except pymysql.MySQLError as e:
            self.stderr.write(self.style.ERROR(f"❌ Connection failed: {e}"))
            return

        try:
            with remote_conn.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

            created, skipped = 0, 0
            with transaction.atomic():
                self.stdout.write("🧹 Deleting all existing Swimlings (and related objects via CASCADE)...")
                Swimling.objects.all().delete()

                for row in rows:
                    try:
                        guardian = User.objects.get(id=row['guardian_id'])
                    except User.DoesNotExist:
                        skipped += 1
                        continue

                    Swimling.objects.create(
                        id=int(row['wp_id']),
                        guardian=guardian,
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        notes=row['notes']
                    )
                    created += 1

                # Reset AUTO_INCREMENT to max(id)+1
                with connection.cursor() as cursor:
                    cursor.execute("SELECT MAX(id) + 1 FROM users_swimling")
                    next_id = cursor.fetchone()[0] or 1
                    cursor.execute(f"ALTER TABLE users_swimling AUTO_INCREMENT = {next_id}")

            self.stdout.write(self.style.SUCCESS(f"✅ Imported {created} Swimlings"))
            if skipped:
                self.stdout.write(self.style.WARNING(f"⚠️ Skipped {skipped} due to missing guardian"))

        finally:
            remote_conn.close()
