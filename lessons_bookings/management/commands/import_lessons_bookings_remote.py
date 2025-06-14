import pymysql
from django.core.management.base import BaseCommand
from lessons_bookings.models import Term, LessonEnrollment
from lessons.models import Product
from users.models import Swimling
from datetime import datetime
from django.utils.timezone import make_aware
from django.db import transaction

def parse_date_safe(date_str):
    if not date_str or str(date_str).startswith("0000"):
        return None
    return date_str

def connect_to_tcsp():
    return pymysql.connect(
        host='tcsp.ie',
        port=3306,
        user='t567715',
        password='0bjs8Pz55Q',
        database='t567715_wp_tcsp',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

class Command(BaseCommand):
    help = 'Fix import of Terms and LessonEnrollments using corrected remote DB field names'

    def handle(self, *args, **options):
        self.stdout.write("\n🌐 Connecting to remote database...")
        try:
            connection = connect_to_tcsp()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Failed to connect: {e}"))
            return

        with connection.cursor() as cursor:
            # TERMS
            self.stdout.write("\n📅 Importing Terms...")
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

            # LESSON ENROLLMENTS
            self.stdout.write("\n📜 Importing Lesson Enrollments...")
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
                        created_dt = make_aware(datetime.strptime(created_dt, "%Y-%m-%d %H:%M:%S"))
                    except:
                        created_dt = None

                if LessonEnrollment.objects.filter(swimling=swimling, lesson=lesson, term=term).exists():
                    skipped += 1
                    continue

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

            self.stdout.write(self.style.SUCCESS(f"\n✅ Lesson Enrollments imported: {imported} / {total} (skipped: {skipped})"))

        connection.close()
        self.stdout.write(self.style.SUCCESS("\n✅ Import process completed."))
