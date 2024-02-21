from django.core.management.base import BaseCommand
import csv
import pymysql



class Command(BaseCommand):
    help = 'Export user swims swims orders, swim order items, Terms data to CSV '

    def connect_to_tcsp(self):
        """Establishes connection to the TCSP database."""
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
            return pymysql.connect(**connection_details)
        except pymysql.MySQLError as e:
            self.stdout.write(self.style.ERROR(f"Error connecting to MySQL Database: {e}"))
            return None

    def execute_query(self, connection, query):
        """Executes a given SQL query and returns the fetched results."""
        if connection is None:
            return []
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except pymysql.MySQLError as e:
            self.stdout.write(self.style.ERROR(f"Error executing query: {e}"))
            return []

    def save_data_to_csv(self, data, filename):
        """Saves fetched data to a CSV file."""
        if data:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

    def handle(self, *args, **options):
        # Queries and corresponding CSV file names
        # Public Swims
        column_names_public_swims = ['id', 'day_id', 'event_id', 'num_places', 'time_start', 'time_end', 'notes',
                                     'active']
        query_public_swims = f"SELECT {', '.join(column_names_public_swims)} FROM mor_sessions_generic"
        # Orders
        column_names_orders = ['wc_order_id as id', 'customer_id as user_id', 'session_id as product_id',
                               'session_date as booking ', 'wc_order_id as stripe_id']
        query_orders = f"SELECT {', '.join(column_names_orders)} FROM mor_generic_bookings WHERE booking_date > '2023-11-25 " \
                       f"12:16:17' AND wc_order_id IS NOT NULL ;"
        # Order Items
        column_names_order_items = ['wc_order_id as id', 'num_adults', 'num_children', 'num_senior', 'num_under3']

        query_order_items = f"SELECT {', '.join(column_names_order_items)} FROM mor_generic_bookings WHERE booking_date > " \
                            f"'2023-11-25 " \
                            f"12:16:17' AND wc_order_id IS NOT NULL ;"

        query_file_pairs = [
            # public_swim_categories
            ("SELECT id, event FROM mor_events", "import_csv/public_swim_categories.csv"),
            # terms
            ("SELECT term_id, start_date, finish_date, COALESCE(rebook_start, '2000-01-01') AS rebook_start, COALESCE"
             "(booking_switch_date, '2000-01-01') AS booking_switch_date, COALESCE(assesments_complete, '2000-01-01') AS assesments_complete FROM mor_terms",
             "import_csv/terms.csv"),
            # Public Swims
            (query_public_swims, "import_csv/public_swims.csv"),
            # Public Swims Orders
            (query_orders, "import_csv/public_swims_orders.csv"),
            # Public Swims Order items
            (query_order_items, "import_csv/public_swims_order_items.csv"),
        ]

        connection = self.connect_to_tcsp()
        if connection:
            try:
                for query, filename in query_file_pairs:
                    data = self.execute_query(connection, query)
                    self.save_data_to_csv(data, filename)
                    self.stdout.write(self.style.SUCCESS(f'Data successfully exported to {filename}'))
            finally:
                connection.close()
