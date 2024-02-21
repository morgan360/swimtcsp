from django.core.management.base import BaseCommand
import csv
import pymysql


class Command(BaseCommand):
    help = 'Exports data from the database to CSV files.'

    def connect_to_tcsp(self):
        connection_details = {
            "host": 'tcsp.ie',
            "port": 3306,
            "user": 't567715',
            "password": '0bjs8Pz55Q',
            "database": 't567715_wp_tcsp',
            "charset": 'utf8mb4',
            "cursorclass": pymysql.cursors.DictCursor
        }
        try:
            connection = pymysql.connect(**connection_details)
            self.stdout.write(self.style.SUCCESS('Successfully connected to the database.'))
            return connection
        except pymysql.MySQLError as e:
            self.stdout.write(self.style.ERROR(f'Error connecting to MySQL Database: {e}'))
            return None

    def execute_query(self, connection, query):
        if connection is None:
            self.stdout.write(self.style.ERROR('No database connection.'))
            return []
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                return results
        except pymysql.MySQLError as e:
            self.stdout.write(self.style.ERROR(f'Error executing query: {e}'))
            return []

    def save_data_to_csv(self, data, filename):
        if data:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            self.stdout.write(self.style.SUCCESS(f'Data written to {filename}'))
        else:
            self.stdout.write(self.style.WARNING(f'No data to write to {filename}'))

    def handle(self, *args, **options):
        connection = self.connect_to_tcsp()
        if connection:
            try:
                column_schools = [
                    'sco_name',
                    'roll_num',
                    'add1',
                    'add2',
                    'add3',
                    'eircode',
                    'phone',
                    'email',
                    'notes',
                ]
                query_schools = f"SELECT {', '.join(column_schools)} FROM t567715_wp_tcsp.sco_schools"

                # Programs
                column_programs = ['Module_ID as id', 'Module as name']
                query_programs = f"SELECT {', '.join(column_programs)} FROM t567715_wp_tcsp.mor_modules"

                # Categories
                column_categories = ['id', 'Module_id as program', 'lesson']
                query_categories = f"SELECT {', '.join(column_categories)} FROM t567715_wp_tcsp.mor_lessons"

                # Lessons
                column_lessons = [
                    'id',
                    'day_id',
                    'lesson_id AS category',  # Renaming 'lesson_id' to 'category'
                    'num_places',
                    'num_weeks',
                    'time_start',
                    'time_end',
                    'active',
                    # Using CASE to convert category_id values
                    'CASE category_id WHEN 19 THEN 47 WHEN 29 THEN 25 ELSE category_id END AS school',
                    # Renaming and converting 'category_id' to 'school'
                    'price',
                ]
                query_lessons = f"SELECT {', '.join(column_lessons)} FROM t567715_wp_tcsp.mor_sessions_classes WHERE category_id IN (19, 29)"

                # School Terms COALESCE gives default date
                column_sco_terms = [
                    "id",
                    "COALESCE(start_date, '2000-01-01') AS start_date",
                    "COALESCE(finish_date, '2000-01-01') AS end_date",
                    "COALESCE(booking_start_date, '2000-01-01') AS booking_start_date",
                    "COALESCE(booking_end_date, '2000-01-01') AS booking_end_date",
                    "COALESCE(assesments_complete, '2000-01-01') AS assessment_date",
                    'CASE category_id WHEN 19 THEN 47 WHEN 29 THEN 25 ELSE category_id END AS school',
                ]
                query_sco_terms = f"SELECT {', '.join(column_sco_terms)} FROM t567715_wp_tcsp.sco_terms WHERE category_id != 88"
                # Data for query
                query_file_pairs = [
                    # Uncomment and add your queries as needed
                    # (query_schools, "schools.csv"),
                    # (query_programs, "programs.csv"),
                    # (query_categories, "categories.csv"),
                    (query_lessons, "import_csv/sco_lessons.csv"),
                    (query_sco_terms, "import_csv/sco_terms.csv"),
                ]
                for query, filename in query_file_pairs:
                    data = self.execute_query(connection, query)
                    self.save_data_to_csv(data, filename)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'An error occurred: {e}'))

            finally:
                if connection:
                    connection.close()
                    self.stdout.write(self.style.SUCCESS('Database connection closed.'))
