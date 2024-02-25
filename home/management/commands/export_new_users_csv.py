from django.core.management.base import BaseCommand
import csv
import pymysql
import phpserialize
import itertools

class Command(BaseCommand):
    help = 'Export user data to CSV and then process it'

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
            return connection
        except pymysql.MySQLError as e:
            self.stdout.write(self.style.ERROR(f"Error connecting to MySQL Database: {e}"))
            return None

    def is_valid_email(self, email):
        if email.startswith('**') or email.startswith('.'):
            return False
        return True

    def deserialize_php(self, serialized_php):
        try:
            return phpserialize.loads(serialized_php.encode(), decode_strings=True)
        except Exception as e:
            print(f"Error deserializing: {e}")
            return None

    def process_data(self, input_file, output_files):
        seen_emails = set()  # Set to track already processed emails

        with open(input_file, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = ['id' if name == 'user_id' else ('email' if name == 'user_email' else name) for name in
                          reader.fieldnames if name != 'Role'] + ['groups']

            writers = []
            outfiles = []
            for file in output_files:
                outfile = open(file, mode='w', newline='', encoding='utf-8')
                outfiles.append(outfile)
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()
                writers.append(writer)

            writer_cycle = itertools.cycle(writers)

            for row in reader:
                user_email = row.get('user_email')
                if not self.is_valid_email(user_email) or user_email in seen_emails:
                    continue  # Skip invalid emails and duplicates

                seen_emails.add(user_email)  # Add email to the set of seen emails

                serialized_role_data = row.get('Role')
                groups = 'customer'
                if serialized_role_data:
                    deserialized_data = self.deserialize_php(serialized_role_data)
                    if deserialized_data and any(deserialized_data.values()):
                        groups = ', '.join([role for role, value in deserialized_data.items() if value])

                new_row = {('id' if key == 'user_id' else ('email' if key == 'user_email' else key)): value for
                           key, value in row.items() if key != 'Role'}
                new_row['groups'] = groups

                next(writer_cycle).writerow(new_row)

        for outfile in outfiles:
            outfile.close()

    def handle(self, *args, **options):
        # Assumes 'query' is defined and correct. Place your SQL query here.
        query = '''
                SELECT
                    u1.ID AS user_id,
                    u1.user_email AS user_email,
                    u1.user_login AS username,
                    m4.meta_value AS mobile_phone,
                    m7.meta_value AS user_phone,
                    m5.meta_value AS Role,
                    m8.meta_value AS notes,
                    m9.meta_value AS other_phone,
                    m10.meta_value AS first_name,
                    m11.meta_value AS last_name
                FROM wpmor_users u1
                LEFT JOIN wpmor_usermeta m4 ON m4.user_id = u1.ID AND m4.meta_key = 'mobile'
                LEFT JOIN wpmor_usermeta m5 ON m5.user_id = u1.ID AND m5.meta_key = 'wpmor_capabilities'
                LEFT JOIN wpmor_usermeta m7 ON m7.user_id = u1.ID AND m7.meta_key = 'user_phone'
                LEFT JOIN wpmor_usermeta m8 ON m8.user_id = u1.ID AND m8.meta_key = 'description'
                LEFT JOIN wpmor_usermeta m9 ON m9.user_id = u1.ID AND m9.meta_key = 'billing_phone'
                LEFT JOIN wpmor_usermeta m10 ON m10.user_id = u1.ID AND m10.meta_key = 'first_name'
                LEFT JOIN wpmor_usermeta m11 ON m11.user_id = u1.ID AND m11.meta_key = 'last_name'
               WHERE u1.ID >= 13146; '''
        connection = self.connect_to_tcsp()
        if connection:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(query)
                    with open('import_csv/new_users.csv', 'w', newline='', encoding='utf-8') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow([i[0] for i in cursor.description])  # Write the header
                        for row in cursor:
                            writer.writerow(row.values())  # Write the data
            finally:
                connection.close()

        # Process the exported CSV and distribute the data
        input_file = 'import_csv/new_users.csv'
        output_files = ['import_csv/new_roles_output_batch1.csv', 'import_csv/new_roles_output_batch2.csv',
                        'import_csv/new_roles_output_batch3.csv', 'import_csv/new_roles_output_batch4.csv']
        self.process_data(input_file, output_files)
