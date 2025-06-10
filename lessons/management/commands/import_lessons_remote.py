import pymysql
from django.core.management.base import BaseCommand
from lessons.models import Program, Category, Product
from django.utils.text import slugify
from datetime import time, datetime
from decouple import config


class Command(BaseCommand):
    help = 'Import Programs, Categories, and Lessons from legacy remote DB into local models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-existing',
            action='store_true',
            help='Delete all existing data before import',
        )

    def handle(self, *args, **options):
        delete_existing = options.get('delete_existing', False)

        if delete_existing:
            self.stdout.write("\n🗑️ Deleting existing data...")
            # Delete in reverse order of dependencies
            Product.objects.all().delete()
            self.stdout.write("   Products deleted.")
            Category.objects.all().delete()
            self.stdout.write("   Categories deleted.")
            Program.objects.all().delete()
            self.stdout.write("   Programs deleted.")

        self.stdout.write("\n🌐 Connecting to remote database...")
        try:
            connection = pymysql.connect(
                host=config('REMOTE_TCSP_DB_HOST'),
                port=config('REMOTE_TCSP_DB_PORT', cast=int),
                user=config('REMOTE_TCSP_DB_USER'),
                password=config('REMOTE_TCSP_DB_PASSWORD'),
                database=config('REMOTE_TCSP_DB_NAME'),
                charset=config('REMOTE_TCSP_DB_CHARSET'),
                cursorclass=pymysql.cursors.DictCursor
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Failed to connect: {e}"))
            return

        try:
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
                               SELECT id,
                                      day_id      AS day_of_week,
                                      lesson_id   AS category,
                                      num_places,
                                      num_weeks,
                                      time_start,
                                      time_end,
                                      active,
                                      category_id AS area,
                                      price
                               FROM mor_sessions_classes
                               WHERE category_id = 18
                               """)

                # Print out day mapping for debugging
                self.stdout.write("\n🔍 Day Mapping in System:")
                for day_value, day_name in Product.DAY_CHOICES:
                    self.stdout.write(f"   {day_value}: {day_name}")

                for row in cursor.fetchall():
                    category = Category.objects.filter(id=row['category']).first()
                    if category:
                        # Convert time fields if needed
                        try:
                            start_time = row['time_start'] if isinstance(row['time_start'],
                                                                         time) else datetime.strptime(
                                str(row['time_start']), '%H:%M:%S').time()
                        except:
                            start_time = time(8, 0)

                        try:
                            end_time = row['time_end'] if isinstance(row['time_end'], time) else datetime.strptime(
                                str(row['time_end']), '%H:%M:%S').time()
                        except:
                            end_time = time(9, 0)

                        # FIX: The day_of_week value is 1-based in the database (1=Monday, 2=Tuesday, etc.)
                        # We need to map it to 0-based (0=Monday, 1=Tuesday, etc.) for Django
                        source_day = row['day_of_week']

                        # Print the raw day value for debugging
                        self.stdout.write(f"Lesson ID {row['id']} raw day_of_week: {source_day}")

                        # Map the day values correctly - this is the key fix
                        if source_day is not None:
                            # Map from 1-7 to 0-6 (Monday=0, Sunday=6)
                            # Assuming source data uses 1=Monday, 7=Sunday
                            try:
                                source_day = int(source_day)
                                if 1 <= source_day <= 7:
                                    day_of_week = source_day - 1
                                else:
                                    # Default to Monday (0) for invalid values
                                    self.stdout.write(self.style.WARNING(
                                        f"⚠️ Lesson ID {row['id']} has invalid day_of_week: {source_day}, mapping to Monday (0)"
                                    ))
                                    day_of_week = 0
                            except (ValueError, TypeError):
                                # Default to Monday for non-integer values
                                self.stdout.write(self.style.WARNING(
                                    f"⚠️ Lesson ID {row['id']} has non-integer day_of_week: {source_day}, mapping to Monday (0)"
                                ))
                                day_of_week = 0
                        else:
                            # Default to Monday for None values
                            self.stdout.write(self.style.WARNING(
                                f"⚠️ Lesson ID {row['id']} has None day_of_week, mapping to Monday (0)"
                            ))
                            day_of_week = 0

                        # Create or update the Product
                        product, created = Product.objects.update_or_create(
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

                        # Log the mapping for verification
                        day_name = dict(Product.DAY_CHOICES).get(day_of_week)
                        self.stdout.write(
                            f"  ✓ Lesson ID {row['id']}: Mapped day {source_day} to {day_of_week} ({day_name})")

                        # Force regenerate the name to ensure it's correct
                        product.name = product.generate_name()
                        product.save(update_fields=['name', 'slug'])
        finally:
            connection.close()
            self.stdout.write("🔒 Connection closed.")

        self.stdout.write(self.style.SUCCESS("\n✅ Import complete."))