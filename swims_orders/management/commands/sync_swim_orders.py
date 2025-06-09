import os
import decimal
import pymysql
from datetime import datetime
from dotenv import load_dotenv

from django.core.management.base import BaseCommand
from swims.models import PublicSwimProduct, PriceVariant
from swims_orders.models import Order, OrderItem
from users.models import User  # Custom user model

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


class Command(BaseCommand):
    help = "Sync public swim orders from remote WordPress DB"

    def handle(self, *args, **options):
        connection = connect_to_remote()
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        query = """
            SELECT wc_order_id,
                   customer_id,
                   session_id,
                   session_date,
                   booking_date,
                   num_adults,
                   num_children,
                   num_senior,
                   num_under3,
                   num_guests,
                   adult_price,
                   child_price,
                   senior_price,
                   under3_price,
                   paid
            FROM mor_generic_bookings
            WHERE booking_date > '2023-11-25 12:16:17'
              AND wc_order_id IS NOT NULL
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        imported_count = 0
        skipped_count = 0
        error_count = 0
        missing_users = 0
        missing_products = 0

        self.stdout.write(f"🔄 Found {len(rows)} swim orders to process...")

        for row in rows:
            try:
                try:
                    user = User.objects.get(id=row['customer_id'])
                except User.DoesNotExist:
                    self.stderr.write(f"⚠️  Skipping order {row['wc_order_id']}: User ID {row['customer_id']} not found.")
                    missing_users += 1
                    continue

                try:
                    product = PublicSwimProduct.objects.get(external_id=row['session_id'])
                except PublicSwimProduct.DoesNotExist:
                    self.stderr.write(f"⚠️  Skipping order {row['wc_order_id']}: Product external ID {row['session_id']} not found.")
                    missing_products += 1
                    continue

                val = row['session_date']
                if isinstance(val, datetime):
                    booking_date = val.date()
                elif isinstance(val, str):
                    booking_date = datetime.strptime(val, '%Y-%m-%d').date()
                else:
                    booking_date = val

                order, created = Order.objects.get_or_create(
                    txId=row['wc_order_id'],
                    defaults={
                        'user': user,
                        'product': product,
                        'booking': booking_date,
                        'amount': 0.0,
                        'paid': row['paid'] == 1,
                        'payment_status': 'Imported',
                    }
                )

                if not created:
                    skipped_count += 1
                    continue  # Already exists

                total = decimal.Decimal("0.00")
                quantities = {
                    'Adult': row['num_adults'],
                    'Child': row['num_children'],
                    'OAP': row['num_senior'],
                    'Infant': row['num_under3']
                }

                for variant_name, qty in quantities.items():
                    if qty and qty > 0:
                        variant = PriceVariant.objects.filter(product=product, variant=variant_name).first()
                        if variant:
                            OrderItem.objects.create(
                                order=order,
                                variant=variant,
                                quantity=qty
                            )
                            total += decimal.Decimal(variant.price) * qty

                order.amount = total
                order.save()
                imported_count += 1

            except Exception as e:
                self.stderr.write(f"❌ Error importing order {row['wc_order_id']}: {e}")
                error_count += 1

        connection.close()
        self.stdout.write(f"✅ Imported {imported_count} new orders.")
        self.stdout.write(f"⏩ Skipped {skipped_count} existing orders.")
        self.stdout.write(f"❌ {error_count} errors encountered.")
        self.stdout.write(f"⚠️  {missing_users} orders skipped due to missing users.")
        self.stdout.write(f"⚠️  {missing_products} orders skipped due to missing products.")
        self.stdout.write("🔒 Connection closed.")
