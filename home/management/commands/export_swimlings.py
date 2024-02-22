from django.core.management.base import BaseCommand
import csv
import pymysql
from django.conf import settings  # Import settings to access custom settings


class Command(BaseCommand):
    help = 'Exports swimlings data to a CSV file'



    def handle(self, *args, **kwargs):
        connection = self.connect_to_tcsp()

        if connection is not None:
            qry = "SELECT id, guardian_id AS guardian, first_name, last_name, notes FROM t567715_wp_tcsp.mor_student_details"
            data = self.execute_query(connection, qry)
            if data:
                self.save_data_to_csv(data, "import_csv/swimlings.csv")
                self.stdout.write(self.style.SUCCESS("Data written to swimlings.csv"))
            else:
                self.stdout.write("No data to write to CSV")

            connection.close()
        else:
            self.stdout.write(self.style.ERROR("Failed to establish database connection."))

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
            connection = pymysql.connect(**connection_details)
            return connection
        except pymysql.MySQLError as e:
            self.stdout.write(f"Error connecting to MySQL Database: {e}")
            return None

    def execute_query(self, connection, query):
        if connection is None:
            self.stdout.write("No database connection.")
            return []
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                return results
        except pymysql.MySQLError as e:
            self.stdout.write(f"Error executing query: {e}")
            return []

    def save_data_to_csv(self, data, filename):
        if data:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
