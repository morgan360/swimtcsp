import os
import pymysql
from dotenv import load_dotenv
from django.core.management.base import BaseCommand
from schools_bookings.models import ScoTerm, ScoEnrollment
from schools.models import ScoSchool, ScoLessons
from users.models import Swimling

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

# Mapping from category_id to ScoSchool ID
CATEGORY_TO_SCHOOL = {
    19: 23,
    29: 1,
}

class Command(BaseCommand):
    help = "Sync school terms and enrollments from remote DB"

    def handle(self, *args, **options):
        connection = connect_to_remote()
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        term_count = enrollment_count = 0
        term_skipped = enrollment_skipped = 0

        # Sync Terms
        self.stdout.write("🔹 Syncing School Terms...")
        cursor.execute("""
            SELECT id,
                   COALESCE(start_date, '2000-01-01') AS start_date,
                   COALESCE(finish_date, '2000-01-01') AS end_date,
                   COALESCE(booking_start_date, '2000-01-01') AS booking_start_date,
                   COALESCE(booking_end_date, '2000-01-01') AS booking_end_date,
                   COALESCE(assesments_complete, '2000-01-01') AS assessment_date,
                   category_id
            FROM sco_terms
        """)
        for row in cursor.fetchall():
            school_id = CATEGORY_TO_SCHOOL.get(row['category_id'])
            school = ScoSchool.objects.filter(id=school_id).first() if school_id else None
            if not school:
                term_skipped += 1
                continue
            _, created = ScoTerm.objects.get_or_create(
                id=row['id'],
                defaults={
                    'start_date': row['start_date'],
                    'end_date': row['end_date'],
                    'booking_start_date': row['booking_start_date'],
                    'booking_end_date': row['booking_end_date'],
                    'assessment_date': row['assessment_date'],
                    'school': school,
                }
            )
            if created:
                term_count += 1
            else:
                term_skipped += 1

        # Sync Enrollments
        self.stdout.write("🔹 Syncing School Enrollments...")
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
            if not (lesson and swimling and term):
                enrollment_skipped += 1
                continue
            _, created = ScoEnrollment.objects.get_or_create(
                id=row['id'],
                defaults={
                    'lesson': lesson,
                    'swimling': swimling,
                    'term': term,
                    'notes': row['notes'],
                    'created': row['created'],
                }
            )
            if created:
                enrollment_count += 1
            else:
                enrollment_skipped += 1

        connection.close()
        self.stdout.write("✅ Sync complete.")
        self.stdout.write(f"🗓️  Terms imported: {term_count}, skipped: {term_skipped}")
        self.stdout.write(f"👥 Enrollments imported: {enrollment_count}, skipped: {enrollment_skipped}")
        self.stdout.write("🔒 Connection closed.")
