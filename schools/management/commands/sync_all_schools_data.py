"""
sync_all_schools_data.py

Django management command to import all school lesson data from the remote TCSP DB:
- Schools
- Programs
- Categories
- Lessons
- Terms
- Enrollments

Use `--delete-existing` to clear all related models before import.
"""

import pymysql
from datetime import time
from dotenv import load_dotenv
from django.core.management.base import BaseCommand
from schools.models import ScoSchool, ScoProgram, ScoCategory, ScoLessons
from schools_bookings.models import ScoTerm, ScoEnrollment
from users.models import Swimling
from decouple import config

load_dotenv()

REMOTE_DB_CONFIG = {
    'host': config('REMOTE_TCSP_DB_HOST'),
    'port': int(config('REMOTE_TCSP_DB_PORT')),
    'user': config('REMOTE_TCSP_DB_USER'),
    'password': config('REMOTE_TCSP_DB_PASSWORD'),
    'database': config('REMOTE_TCSP_DB_NAME'),
    'charset': config('REMOTE_TCSP_DB_CHARSET', 'utf8mb4'),
}

def connect_to_remote():
    return pymysql.connect(**REMOTE_DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

class Command(BaseCommand):
    help = "Sync all school lesson-related data from remote TCSP DB"

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-existing',
            action='store_true',
            help='Delete all existing school data before import'
        )

    def handle(self, *args, **options):
        delete_existing = options.get('delete_existing')

        if delete_existing:
            self.stdout.write("🧹 Deleting existing school data...")
            ScoEnrollment.objects.all().delete()
            ScoTerm.objects.all().delete()
            ScoLessons.objects.all().delete()
            ScoCategory.objects.all().delete()
            ScoProgram.objects.all().delete()
            ScoSchool.objects.all().delete()
            self.stdout.write("✅ Deletion complete.\n")

        self.stdout.write("🌐 Connecting to remote database...")
        connection = connect_to_remote()
        cursor = connection.cursor()

        # SCHOOLS
        self.stdout.write("🏫 Importing Schools...")
        cursor.execute("""
            SELECT id, sco_name, roll_num, add1, add2, add3, eircode, phone, email, notes 
            FROM sco_schools
        """)
        for row in cursor.fetchall():
            ScoSchool.objects.update_or_create(
                id=row['id'],
                defaults={
                    'sco_role_num': row['roll_num'],
                    'name': row['sco_name'],
                    'add1': row['add1'], 'add2': row['add2'], 'add3': row['add3'],
                    'eircode': row['eircode'], 'phone': row['phone'],
                    'email': row['email'], 'notes': row['notes']
                }
            )

        # PROGRAMS
        self.stdout.write("📘 Importing Programs...")
        cursor.execute("SELECT Module_ID as id, Module as name FROM mor_modules")
        for row in cursor.fetchall():
            ScoProgram.objects.get_or_create(id=row['id'], defaults={'name': row['name']})

        # CATEGORIES
        self.stdout.write("📂 Importing Categories (used in school lessons only)...")
        cursor.execute("""
            SELECT DISTINCT ml.id, ml.Module_id AS program, ml.lesson AS name
            FROM mor_lessons ml
            JOIN mor_sessions_classes sc ON ml.id = sc.lesson_id
            WHERE sc.category_id IN (19, 29)
        """)
        for row in cursor.fetchall():
            program = ScoProgram.objects.filter(id=row['program']).first()
            if program:
                ScoCategory.objects.get_or_create(
                    id=row['id'],
                    defaults={'program': program, 'name': row['name']}
                )
            else:
                self.stderr.write(f"❌ Skipping category {row['id']} — missing program {row['program']}")

        # LESSONS
        self.stdout.write("📅 Importing Lessons...")
        cursor.execute("""
                       SELECT id,
                              day_id,
                              lesson_id AS category,
                              num_places,
                              num_weeks,
                              time_start,
                              time_end,
                              active,
                              CASE category_id
                                  WHEN 19 THEN 23
                                  WHEN 29 THEN 1
                                  END   AS school,
                              price
                       FROM mor_sessions_classes
                       WHERE category_id IN (19, 29)

                       """)
        for row in cursor.fetchall():
            category = ScoCategory.objects.filter(id=row['category']).first()
            school = ScoSchool.objects.filter(id=row['school']).first()
            if not (category and school):
                self.stderr.write(f"⚠️ Skipping lesson {row['id']} (missing category or school)")
                if not category:
                    self.stderr.write(f"   ❌ Missing category ID {row['category']}")
                if not school:
                    self.stderr.write(f"   ❌ Missing school ID {row['school']}")
                continue

            try:
                start_time = row['time_start'] if isinstance(row['time_start'], time) else time.fromisoformat(str(row['time_start']))
                end_time = row['time_end'] if isinstance(row['time_end'], time) else time.fromisoformat(str(row['time_end']))
            except Exception as e:
                self.stderr.write(f"⚠️  Skipping lesson {row['id']} due to invalid time: {e}")
                continue

            try:
                ScoLessons.objects.create(
                    id=row['id'],
                    category=category,
                    school=school,
                    day_of_week=row['day_id'],
                    num_places=row['num_places'],
                    num_weeks=row['num_weeks'],
                    start_time=start_time,
                    end_time=end_time,
                    price=row['price'],
                    active=row['active'] == 1
                )
            except Exception as e:
                self.stderr.write(f"❌ Failed to create lesson {row['id']}: {e}")
                import traceback
                traceback.print_exc()

        # TERMS
        self.stdout.write("🗓️  Importing Terms...")
        cursor.execute("""
                       SELECT id,
                              COALESCE(start_date, '2000-01-01')          AS start_date,
                              COALESCE(finish_date, '2000-01-01')         AS end_date,
                              COALESCE(booking_start_date, '2000-01-01')  AS booking_start_date,
                              COALESCE(booking_end_date, '2000-01-01')    AS booking_end_date,
                              COALESCE(assesments_complete, '2000-01-01') AS assessment_date,
                              category_id
                       FROM sco_terms
                       """)
        for row in cursor.fetchall():
            # Map category_id → known school IDs
            school_map = {19: 23, 29: 1}
            school_id = school_map.get(row['category_id'])

            if not school_id:
                self.stderr.write(f"❌ Unknown school mapping for term {row['id']} (category {row['category_id']})")
                continue

            school = ScoSchool.objects.filter(id=school_id).first()
            if not school:
                self.stderr.write(f"❌ School ID {school_id} not found for term {row['id']}")
                continue

            ScoTerm.objects.get_or_create(
                id=row['id'],
                defaults={
                    'start_date': row['start_date'],
                    'end_date': row['end_date'],
                    'booking_start_date': row['booking_start_date'],
                    'booking_end_date': row['booking_end_date'],
                    'assessment_date': row['assessment_date'],
                    'school': school
                }
            )

        # ENROLLMENTS
        self.stdout.write("👥 Importing Enrollments...")
        cursor.execute("""
            SELECT mor_class_bookings.id,
                   mor_class_bookings.student_id AS swimling,
                   mor_class_bookings.session_id AS lesson,
                   mor_class_bookings.term_id AS term,
                   mor_class_bookings.wc_order_id AS notes,
                   mor_class_bookings.booking_date AS created
            FROM mor_class_bookings
            JOIN mor_sessions_classes ON mor_class_bookings.session_id = mor_sessions_classes.id
            WHERE mor_sessions_classes.category_id IN (19, 29)
              AND mor_class_bookings.term_id > 40
              AND mor_class_bookings.paid = 1
        """)
        for row in cursor.fetchall():
            lesson = ScoLessons.objects.filter(id=row['lesson']).first()
            swimling = Swimling.objects.filter(id=row['swimling']).first()
            term = ScoTerm.objects.filter(id=row['term']).first()

            if not (lesson and term and swimling):
                self.stderr.write(f"⚠️ Skipping enrollment {row['id']}:")
                if not lesson:
                    self.stderr.write(f"   ❌ Lesson ID {row['lesson']} not found")
                if not term:
                    self.stderr.write(f"   ❌ Term ID {row['term']} not found")
                if not swimling:
                    self.stderr.write(f"   ❌ Swimling ID {row['swimling']} not found")
                continue

            ScoEnrollment.objects.get_or_create(
                id=row['id'],
                defaults={
                    'lesson': lesson,
                    'swimling': swimling,
                    'term': term,
                    'notes': row['notes'],
                    'created': row['created']
                }
            )

        connection.close()
        self.stdout.write(self.style.SUCCESS("\n✅ School data sync complete."))
