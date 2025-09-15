import pymysql
from decouple import config
from django.core.management.base import BaseCommand
from users.models import Swimling, User
from django.db import connection, transaction
from datetime import datetime, date

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
                       notes,
                       dob
                FROM mor_student_details \
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
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠️ Skipped Swimling ID {row['wp_id']}: Guardian ID {row['guardian_id']} not found"
                            )
                        )
                        continue

                    # Safe field extraction with fallback
                    first_name = row.get('first_name') or 'Unknown'
                    last_name = row.get('last_name') or ''
                    notes = row.get('notes') or ''

                    raw_dob = row.get('dob')
                    dob = None

                    if raw_dob and raw_dob not in ("0000-00-00", "0000-00-00 00:00:00"):
                        if isinstance(raw_dob, date):
                            # Already a date object
                            dob = raw_dob
                        else:
                            try:
                                dob = datetime.strptime(raw_dob, "%Y-%m-%d").date()
                            except ValueError:
                                try:
                                    dob = datetime.strptime(raw_dob, "%d/%m/%Y").date()
                                except ValueError:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"⚠️ Could not parse DOB '{raw_dob}' for Swimling {row['wp_id']}")
                                    )
                    Swimling.objects.create(
                        id=int(row['wp_id']),
                        guardian=guardian,
                        first_name=first_name,
                        last_name=last_name,
                        notes=notes,
                        dob=dob  # assuming your Swimling model has a DateField
                    )

                # Reset AUTO_INCREMENT to max(id)+1
                with connection.cursor() as cursor:
                    cursor.execute("SELECT MAX(id) + 1 FROM users_swimling")
                    next_id = cursor.fetchone()[0] or 1
                    cursor.execute(f"ALTER TABLE users_swimling AUTO_INCREMENT = {next_id}")

            self.stdout.write(self.style.SUCCESS(f"✅ Imported {created} Swimlings"))
            if skipped:
                self.stdout.write(self.style.WARNING(f"⚠️ Skipped {skipped} due to missing guardians"))

        finally:
            remote_conn.close()
            self.stdout.write("🔒 Remote DB connection closed.")
