"""
sync_all_public_lessons_data.py

Django management command to import and sync all public lesson-related data
from a remote legacy TCSP database into the local PostgreSQL database.

This script performs the following in strict sequence:
1. Optionally deletes existing Programs, Categories, Products, Terms, and Enrollments
2. Connects once to the remote WordPress/MySQL database
3. Imports:
   - Programs (e.g., 'Junior', 'Senior')
   - Categories (e.g., 'Beginner', 'Advanced')
   - Lessons (Products with times, days, places)
   - Term definitions with booking/rebooking dates
   - LessonEnrollments (swimlings assigned to lessons per term)

Requirements:
- Remote DB credentials must be set via environment variables (.env or system)
- Uses decouple for config and pymysql for DB connection
- Must run inside a Django project context

Usage:
    python manage.py sync_all_public_lessons_data --delete-existing

Author: [Morgan]
Date: [25-Jun-2025]
"""


import os
import pymysql
from datetime import datetime, time
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.utils.timezone import make_aware, is_naive
from decouple import config
from lessons.models import Program, Category, Product
from lessons_bookings.models import Term, LessonEnrollment
from users.models import Swimling

def parse_date_safe(date_str):
    if not date_str or str(date_str).startswith("0000"):
        return None
    return date_str


class Command(BaseCommand):
    help = "Sync Programs, Categories, Lessons, Terms and Enrollments from legacy remote DB"

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-existing',
            action='store_true',
            help='Delete all existing data before import'
        )

    def handle(self, *args, **options):
        delete_existing = options.get('delete_existing')

        if delete_existing:
            self.stdout.write("🗑️ Deleting existing lesson data...")
            LessonEnrollment.objects.all().delete()
            Term.objects.all().delete()
            Product.objects.all().delete()
            Category.objects.all().delete()
            Program.objects.all().delete()
            self.stdout.write("✅ Existing data deleted.\n")

        self.stdout.write("🌐 Connecting to remote database...")

        try:
            connection = pymysql.connect(
                host=config('REMOTE_TCSP_DB_HOST'),
                port=int(config('REMOTE_TCSP_DB_PORT')),
                user=config('REMOTE_TCSP_DB_USER'),
                password=config('REMOTE_TCSP_DB_PASSWORD'),
                database=config('REMOTE_TCSP_DB_NAME'),
                charset=config('REMOTE_TCSP_DB_CHARSET', 'utf8mb4'),
                cursorclass=pymysql.cursors.DictCursor
            )
        except Exception as e:
            self.stderr.write(f"❌ Failed to connect to remote DB: {e}")
            return

        try:
            with connection.cursor() as cursor:
                # Programs
                self.stdout.write("📦 Importing Programs...")
                cursor.execute("SELECT Module_ID AS id, Module AS name FROM mor_modules")
                for row in cursor.fetchall():
                    Program.objects.update_or_create(id=row['id'], defaults={'name': row['name']})

                # Categories
                CATEGORY_NAME_MAPPING = {
                    "Lengths - L3": {"new_name": "Lengths(l3)", "short_name": "Len~l3"},
                    "Advanced": {"new_name": "Advanced", "short_name": "Adv"},
                    "Lengths - L2": {"new_name": "Lengths(l2)", "short_name": "Len~l2"},
                    "Lengths - L1": {"new_name": "Lengths(l1)", "short_name": "Len~l1"},
                    "Improvers - 1": {"new_name": "Improvers(1)", "short_name": "Imp~1"},
                    "Improvers - 2": {"new_name": "Improvers(2)", "short_name": "Imp~2"},
                    "Improvers - C": {"new_name": "Improvers(c)", "short_name": "Imp~c"},
                    "Beginners - 1": {"new_name": "Beginners(1)", "short_name": "Beg~1"},
                    "Beginners - 2": {"new_name": "Beginners(2)", "short_name": "Beg~2"},
                    "Beginners - C": {"new_name": "Beginners(c)", "short_name": "Beg~c"},
                    "Adult Begin & Improvers": {"new_name": "Adult Begin & Improvers", "short_name": "Adult~Beg:Imp"},
                    "Beginners 1 - BG": {"new_name": "Beginners 1(s)", "short_name": "Beg1~(s)"},
                    "Improvers 1 - BG": {"new_name": "Improvers 1(s))", "short_name": "Imp1~(s)"},
                    "Improvers 2 - BG": {"new_name": "Improvers 2(s)", "short_name": "Imp2~(s)"},
                    "Advanced - BG": {"new_name": "Advanced(s)", "short_name": "Adv(s)"},
                    "Test Classes": {"new_name": "Test", "short_name": "Test"},
                    "Beginners 2 - BG": {"new_name": "Beginners 2(s))", "short_name": "Beg2~(s)"},
                    "Beginners 8+": {"new_name": "Beginners(8+)", "short_name": "Beg~8+"},

                }

                self.stdout.write("📂 Importing Categories...")
                cursor.execute("SELECT id, Module_id AS program, lesson AS name FROM mor_lessons")

                for row in cursor.fetchall():
                    program = Program.objects.filter(id=row['program']).first()
                    if not program:
                        continue

                    original_name = row['name']
                    mapped = CATEGORY_NAME_MAPPING.get(original_name, {})
                    new_name = mapped.get('new_name', original_name)
                    short_name = mapped.get('short_name', None)

                    Category.objects.update_or_create(
                        id=row['id'],
                        defaults={
                            'name': new_name,
                            'short_name': short_name,
                            'program': program,
                            'slug': slugify(new_name)
                        }
                    )

                # Lessons (Products)
                self.stdout.write("📚 Importing Lessons...")
                cursor.execute("""
                    SELECT id, day_id AS day_of_week, lesson_id AS category, num_places,
                           num_weeks, time_start, time_end, active, category_id AS area, price
                    FROM mor_sessions_classes
                    WHERE category_id = 18
                """)
                for row in cursor.fetchall():
                    category = Category.objects.filter(id=row['category']).first()
                    if not category:
                        continue

                    # Convert day_of_week 1-7 to 0-6
                    source_day = int(row['day_of_week']) if row['day_of_week'] else 1
                    day_of_week = source_day - 1 if 1 <= source_day <= 7 else 0

                    try:
                        start_time = row['time_start'] if isinstance(row['time_start'], time) else datetime.strptime(str(row['time_start']), '%H:%M:%S').time()
                        end_time = row['time_end'] if isinstance(row['time_end'], time) else datetime.strptime(str(row['time_end']), '%H:%M:%S').time()
                    except:
                        start_time, end_time = time(8, 0), time(9, 0)

                    product, _ = Product.objects.update_or_create(
                        id=row['id'],
                        defaults={
                            'day_of_week': day_of_week,
                            'category': category,
                            'num_places': row['num_places'],
                            'num_weeks': row['num_weeks'],
                            'start_time': start_time,
                            'end_time': end_time,
                            'price': row['price'] or 0,
                            'active': row['active'] == 1
                        }
                    )
                    product.name = product.generate_name()
                    product.save(update_fields=['name', 'slug'])

                self.stdout.write("✅ Lessons imported.\n")

                # Terms
                self.stdout.write("📅 Importing Terms...")
                cursor.execute("""
                    SELECT term_id, start_date, finish_date,
                           rebook_start AS rebooking_date,
                           booking_switch_date AS booking_date,
                           assesments_complete AS assessment_date
                    FROM mor_terms
                """)
                for row in cursor.fetchall():
                    if row['term_id'] == 0:
                        continue
                    Term.objects.update_or_create(
                        id=row['term_id'],
                        defaults={
                            'start_date': parse_date_safe(row['start_date']),
                            'end_date': parse_date_safe(row['finish_date']),
                            'rebooking_date': parse_date_safe(row['rebooking_date']),
                            'booking_date': parse_date_safe(row['booking_date']),
                            'assessment_date': parse_date_safe(row['assessment_date'])
                        }
                    )

                self.stdout.write("✅ Terms imported.\n")

                # Enrollments
                self.stdout.write("📜 Importing Enrollments...")
                cursor.execute("""
                    SELECT id, student_id AS swimling_id,
                           session_id AS lesson_id,
                           term_id, wc_order_id AS notes,
                           booking_date AS created
                    FROM mor_class_bookings
                """)

                total = imported = skipped = 0
                for row in cursor.fetchall():
                    total += 1
                    try:
                        swimling = Swimling.objects.get(id=row['swimling_id'])
                        lesson = Product.objects.get(id=row['lesson_id'])
                        term = Term.objects.get(id=row['term_id'])
                    except (Swimling.DoesNotExist, Product.DoesNotExist, Term.DoesNotExist):
                        skipped += 1
                        continue

                    created_dt = row['created']
                    if isinstance(created_dt, str):
                        try:
                            created_dt = datetime.strptime(created_dt, "%Y-%m-%d %H:%M:%S")
                        except:
                            created_dt = None

                    # Make it timezone-aware if it's naive
                    if isinstance(created_dt, datetime) and is_naive(created_dt):
                        try:
                            created_dt = make_aware(created_dt)
                        except:
                            created_dt = None

                    LessonEnrollment.objects.update_or_create(
                        swimling=swimling,
                        lesson=lesson,
                        term=term,
                        defaults={
                            'notes': row['notes'],
                            'created': created_dt or None
                        }
                    )
                    imported += 1

                self.stdout.write(self.style.SUCCESS(
                    f"\n✅ Lesson Enrollments imported: {imported} / {total} (skipped: {skipped})"
                ))

        finally:
            connection.close()
            self.stdout.write("🔒 Remote DB connection closed.")
