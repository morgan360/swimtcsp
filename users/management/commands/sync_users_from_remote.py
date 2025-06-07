import csv
import pymysql
import phpserialize

from django.core.management.base import BaseCommand
from users.resources import UserResource
from tablib import Dataset


class Command(BaseCommand):
    help = "Sync users from remote WordPress database and import into local DB via import-export"

    def handle(self, *args, **kwargs):
        # Connect to remote MySQL
        connection_details = {
            "host": 'tcsp.ie',
            "port": 3306,
            "user": 't567715',
            "password": '0bjs8Pz55Q',
            "database": 't567715_wp_tcsp',
            "charset": 'utf8mb4',
            "cursorclass": pymysql.cursors.DictCursor
        }

        query = '''
        SELECT
            u1.ID AS user_id,
            u1.user_email AS user_email,
            u1.user_login AS username,
            m4.meta_value AS mobile_phone,
            m7.meta_value AS user_phone,
            m5.meta_value AS Role,
            m8.meta_value AS notes,
            m9.meta_value AS other_phone,
            m10.meta_value AS first_name,
            m11.meta_value AS last_name
        FROM wpmor_users u1
        LEFT JOIN wpmor_usermeta m4 ON m4.user_id = u1.ID AND m4.meta_key = 'mobile'
        LEFT JOIN wpmor_usermeta m5 ON m5.user_id = u1.ID AND m5.meta_key = 'wpmor_capabilities'
        LEFT JOIN wpmor_usermeta m7 ON m7.user_id = u1.ID AND m7.meta_key = 'user_phone'
        LEFT JOIN wpmor_usermeta m8 ON m8.user_id = u1.ID AND m8.meta_key = 'description'
        LEFT JOIN wpmor_usermeta m9 ON m9.user_id = u1.ID AND m9.meta_key = 'billing_phone'
        LEFT JOIN wpmor_usermeta m10 ON m10.user_id = u1.ID AND m10.meta_key = 'first_name'
        LEFT JOIN wpmor_usermeta m11 ON m11.user_id = u1.ID AND m11.meta_key = 'last_name'
        '''

        try:
            conn = pymysql.connect(**connection_details)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ MySQL connection failed: {e}"))
            return

        dataset = Dataset()
        seen = set()

        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()

            for row in results:
                email = row.get("user_email", "")
                if not email or email.startswith("**") or email.startswith(".") or email in seen:
                    continue

                seen.add(email)

                try:
                    roles_raw = row.get("Role", "")
                    roles = "customer"
                    if roles_raw:
                        decoded = phpserialize.loads(roles_raw.encode(), decode_strings=True)
                        roles = ", ".join([r for r, v in decoded.items() if v])
                except Exception as e:
                    self.stderr.write(self.style.WARNING(f"⚠️ Role parse error for {email}: {e}"))
                    roles = "customer"

                dataset.append((
                    row.get("user_id"),
                    email,
                    row.get("username") or "",
                    row.get("first_name") or "",
                    row.get("last_name") or "",
                    row.get("mobile_phone") or "",
                    row.get("other_phone") or row.get("user_phone") or "",
                    row.get("notes") or "",
                    roles
                ))

            dataset.headers = [
                "id", "email", "username", "first_name", "last_name",
                "mobile_phone", "other_phone", "notes", "groups"
            ]

            resource = UserResource()
            result = resource.import_data(dataset, dry_run=False, raise_errors=True)

            self.stdout.write(self.style.SUCCESS(f"✅ {len(dataset)} users imported successfully."))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Failed to import users: {e}"))
        finally:
            conn.close()
