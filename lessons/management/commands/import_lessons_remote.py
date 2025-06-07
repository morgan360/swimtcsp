import pymysql
from django.core.management.base import BaseCommand
from lessons.models import Program, Category, Product
from django.utils.text import slugify
from datetime import time, datetime


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
    help = 'Import Programs, Categories, and Lessons from legacy remote DB into local models'

    def handle(self, *args, **options):
        self.stdout.write("\n🌐 Connecting to remote database...")
        try:
            connection = connect_to_tcsp()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Failed to connect: {e}"))
            return

        with connection.cursor() as cursor:
            # Import Programs
            self.stdout.write("\n📦 Importing Programs...")
            cursor.execute("SELECT Module_ID AS id, Module AS name FROM mor_modules")
            for row in cursor.fetchall():
                Program.objects.update_or_create(id=row['id'], defaults={'name': row['name']})

            # Import Categories (must follow programs)
            self.stdout.write("\n📂 Importing Categories...")
            cursor.execute("SELECT id, Module_id AS program, lesson AS name FROM mor_lessons")
            for row in cursor.fetchall():
                program = Program.objects.filter(id=row['program']).first()
                if program:
                    Category.objects.update_or_create(
                        id=row['id'],
                        defaults={
                            'name': row['name'],
                            'program': program,
                            'slug': slugify(row['name'])
                        }
                    )

            # Import Lessons (must follow categories)
            self.stdout.write("\n📚 Importing Lessons (Products)...")
            cursor.execute("""
                SELECT id, day_id AS day_of_week, lesson_id AS category,
                       num_places, num_weeks, time_start, time_end, active,
                       category_id AS area, price
                FROM mor_sessions_classes WHERE category_id = 18
            """)

            for row in cursor.fetchall():
                category = Category.objects.filter(id=row['category']).first()
                if category:
                    # Convert time fields if needed
                    try:
                        start_time = row['time_start'] if isinstance(row['time_start'], time) else datetime.strptime(str(row['time_start']), '%H:%M:%S').time()
                    except:
                        start_time = time(8, 0)

                    try:
                        end_time = row['time_end'] if isinstance(row['time_end'], time) else datetime.strptime(str(row['time_end']), '%H:%M:%S').time()
                    except:
                        end_time = time(9, 0)

                    Product.objects.update_or_create(
                        id=row['id'],
                        defaults={
                            'day_of_week': row['day_of_week'],
                            'category': category,
                            'num_places': row['num_places'],
                            'num_weeks': row['num_weeks'],
                            'start_time': start_time,
                            'end_time': end_time,
                            'price': row['price'] or 0,
                            'active': row['active'] == 1
                        }
                    )

        connection.close()
        self.stdout.write(self.style.SUCCESS("\n✅ Import complete."))
