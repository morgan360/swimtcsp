import os
import pymysql
from datetime import datetime, time
from dotenv import load_dotenv

from django.core.management.base import BaseCommand
from schools.models import ScoSchool, ScoProgram, ScoCategory, ScoLessons

load_dotenv()

REMOTE_DB_CONFIG = {
    'host': os.getenv('REMOTE_TCSP_DB_HOST'),
    'port': int(os.getenv('REMOTE_TCSP_DB_PORT')),
    'user': os.getenv('REMOTE_TCSP_DB_USER'),
    'password': os.getenv('REMOTE_TCSP_DB_PASSWORD'),
    'database': os.getenv('REMOTE_TCSP_DB_NAME'),
    'charset': os.getenv('REMOTE_TCSP_DB_CHARSET', 'utf8mb4'),
}

def connect_to_remote():
    return pymysql.connect(**REMOTE_DB_CONFIG)

class Command(BaseCommand):
    help = "Sync schools, programs, categories, and lessons from remote DB"

    def handle(self, *args, **options):
        connection = connect_to_remote()
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        school_count = 0
        school_skipped = 0
        program_count = 0
        program_skipped = 0
        category_count = 0
        category_skipped = 0
        lesson_count = 0
        lesson_skipped = 0

        # Schools
        self.stdout.write("🔹 Syncing Schools...")
        cursor.execute("SELECT sco_name, roll_num, add1, add2, add3, eircode, phone, email, notes FROM sco_schools")
        for row in cursor.fetchall():
            school, created = ScoSchool.objects.get_or_create(
                sco_role_num=row['roll_num'],
                defaults={
                    'name': row['sco_name'],
                    'add1': row['add1'],
                    'add2': row['add2'],
                    'add3': row['add3'],
                    'eircode': row['eircode'],
                    'phone': row['phone'],
                    'email': row['email'],
                    'notes': row['notes'],
                }
            )
            if created:
                school_count += 1
            else:
                school_skipped += 1

        # Programs
        self.stdout.write("🔹 Syncing Programs...")
        cursor.execute("SELECT Module_ID as id, Module as name FROM mor_modules")
        for row in cursor.fetchall():
            program, created = ScoProgram.objects.get_or_create(id=row['id'], defaults={'name': row['name']})
            if created:
                program_count += 1
            else:
                program_skipped += 1

        # Categories
        self.stdout.write("🔹 Syncing Categories...")
        cursor.execute("SELECT id, Module_id as program, lesson as name FROM mor_lessons")
        for row in cursor.fetchall():
            program = ScoProgram.objects.filter(id=row['program']).first()
            if not program:
                continue
            category, created = ScoCategory.objects.get_or_create(
                id=row['id'],
                defaults={
                    'program': program,
                    'name': row['name'],
                }
            )
            if created:
                category_count += 1
            else:
                category_skipped += 1

        # Lessons
        self.stdout.write("🔹 Syncing Lessons...")
        lesson_query = """
            SELECT id, day_id, lesson_id AS category,
                   num_places, num_weeks,
                   time_start, time_end,
                   active,
                   CASE category_id
                       WHEN 19 THEN 47
                       WHEN 29 THEN 25
                       ELSE category_id
                   END AS school,
                   price
            FROM mor_sessions_classes
            WHERE category_id IN (19, 29)
        """
        cursor.execute(lesson_query)
        for row in cursor.fetchall():
            category = ScoCategory.objects.filter(id=row['category']).first()
            school = ScoSchool.objects.filter(id=row['school']).first()
            if not category:
                continue

            try:
                start_time = row['time_start'] if isinstance(row['time_start'], time) else time.fromisoformat(str(row['time_start']))
                end_time = row['time_end'] if isinstance(row['time_end'], time) else time.fromisoformat(str(row['time_end']))
            except Exception as e:
                self.stderr.write(f"⚠️  Skipping lesson {row['id']}: Invalid time format → {e}")
                lesson_skipped += 1
                continue

            _, created = ScoLessons.objects.get_or_create(
                id=row['id'],
                defaults={
                    'category': category,
                    'school': school,
                    'day_of_week': row['day_id'],
                    'num_places': row['num_places'],
                    'num_weeks': row['num_weeks'],
                    'start_time': start_time,
                    'end_time': end_time,
                    'price': row['price'],
                    'active': row['active'] == 1,
                }
            )
            if created:
                lesson_count += 1
            else:
                lesson_skipped += 1

        connection.close()
        self.stdout.write("✅ Sync complete.")
        self.stdout.write(f"🏫 Schools imported: {school_count}, skipped: {school_skipped}")
        self.stdout.write(f"📘 Programs imported: {program_count}, skipped: {program_skipped}")
        self.stdout.write(f"📚 Categories imported: {category_count}, skipped: {category_skipped}")
        self.stdout.write(f"📅 Lessons imported: {lesson_count}, skipped: {lesson_skipped}")
        self.stdout.write("🔒 Connection closed.")
