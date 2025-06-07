
import pymysql
from django.core.management.base import BaseCommand
from users.models import Swimling, User

class Command(BaseCommand):
    help = 'Import Swimlings from remote WordPress DB into local Django DB'

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
        SELECT id AS wp_student_id,
               guardian_id,
               first_name,
               last_name,
               notes
        FROM t567715_wp_tcsp.mor_student_details
        """

        try:
            self.stdout.write("🔌 Connecting to remote database...")
            connection = pymysql.connect(**connection_details)
        except pymysql.MySQLError as e:
            self.stderr.write(f"❌ Connection failed: {e}")
            return

        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()

                created, skipped = 0, 0
                for row in results:
                    try:
                        guardian = User.objects.get(id=row['guardian_id'])
                    except User.DoesNotExist:
                        skipped += 1
                        continue

                    swimling, _ = Swimling.objects.update_or_create(
                        wp_student_id=row['wp_student_id'],
                        defaults={
                            'guardian': guardian,
                            'first_name': row['first_name'],
                            'last_name': row['last_name'],
                            'notes': row['notes']
                        }
                    )
                    created += 1

                self.stdout.write(self.style.SUCCESS(f"✅ Imported {created} Swimlings"))
                self.stdout.write(self.style.WARNING(f"⚠️ Skipped {skipped} due to missing guardian"))
        finally:
            connection.close()
