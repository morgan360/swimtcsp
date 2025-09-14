import os
import decimal
import pymysql
from datetime import datetime, time, timedelta
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from decouple import config
from dotenv import load_dotenv

from swims.models import PublicSwimCategory, PublicSwimProduct, PriceVariant
from swims_orders.models import Order, OrderItem
from users.models import User  # custom user

from django.db import connection

load_dotenv()

DAY_CHOICES = {
    0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday',
    4: 'Friday', 5: 'Saturday', 6: 'Sunday'
}

REMOTE_DB_CONFIG = {
    'host': config('REMOTE_TCSP_DB_HOST'),
    'port': int(config('REMOTE_TCSP_DB_PORT')),
    'user': config('REMOTE_TCSP_DB_USER'),
    'password': config('REMOTE_TCSP_DB_PASSWORD'),
    'database': config('REMOTE_TCSP_DB_NAME'),
    'charset': config('REMOTE_TCSP_DB_CHARSET', 'utf8mb4'),
}


def safe_time(val):
    if isinstance(val, time):
        return val.replace(second=0, microsecond=0)
    if isinstance(val, timedelta):
        total_seconds = int(val.total_seconds())
        return time(hour=(total_seconds // 3600) % 24, minute=(total_seconds % 3600) // 60)
    return None


class Command(BaseCommand):
    help = "Sync Public Swim data and orders from remote TCSP DB (forcing remote IDs as PKs)"

    def handle(self, *args, **options):
        # === STEP 1: RESET LOCAL TABLES ===
        self.stdout.write("🧹 Resetting related tables...")
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        PriceVariant.objects.all().delete()
        PublicSwimProduct.objects.all().delete()
        PublicSwimCategory.objects.all().delete()

        # bump AUTO_INCREMENT high so new objects don't clash
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE swims_orders_orderitem AUTO_INCREMENT = 100000;")
            cursor.execute("ALTER TABLE swims_orders_order AUTO_INCREMENT = 100000;")
            cursor.execute("ALTER TABLE swims_pricevariant AUTO_INCREMENT = 100000;")
            cursor.execute("ALTER TABLE swims_publicswimproduct AUTO_INCREMENT = 100000;")
            cursor.execute("ALTER TABLE swims_publicswimcategory AUTO_INCREMENT = 100000;")

        self.stdout.write("✅ Tables cleared and reset.")

        # === STEP 2: Connect to remote DB ===
        self.stdout.write("🔗 Connecting to remote DB...")
        conn = pymysql.connect(**REMOTE_DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)

        try:
            with conn.cursor() as cursor:
                # === STEP 3: Categories ===
                self.stdout.write("📦 Importing categories...")
                cursor.execute("SELECT id, event FROM mor_events")
                events = cursor.fetchall()
                event_map = {}
                for e in events:
                    cat, _ = PublicSwimCategory.objects.update_or_create(
                        id=e['id'],  # force PK
                        defaults={
                            'name': e['event'],
                            'slug': slugify(e['event']),
                            'description': ''
                        }
                    )
                    event_map[e['id']] = cat
                self.stdout.write(f"✅ {len(event_map)} categories synced.")

                # === STEP 4: Products ===
                self.stdout.write("📦 Importing products...")
                cursor.execute("""
                    SELECT id, day_id, event_id, num_places, time_start, time_end, notes, active 
                    FROM mor_sessions_generic
                """)
                sessions = cursor.fetchall()
                product_map = {}

                for s in sessions:
                    category = event_map.get(s['event_id'])
                    if not category:
                        continue

                    start_time = safe_time(s['time_start'])
                    time_str = start_time.strftime('%H%M') if start_time else '0000'
                    slug = slugify(f"{category.slug}-{s['day_id']}-{time_str}")
                    name = f"{category.name} ({DAY_CHOICES.get(s['day_id'], 'Unknown')} {time_str})"

                    product, _ = PublicSwimProduct.objects.update_or_create(
                        id=s['id'],  # force PK
                        defaults={
                            'slug': slug,
                            'name': name,
                            'category': category,
                            'start_time': start_time,
                            'end_time': safe_time(s['time_end']),
                            'day_of_week': s['day_id'],
                            'num_places': s['num_places'],
                            'available': bool(s['active']),
                        }
                    )
                    product_map[s['id']] = product

                self.stdout.write(f"✅ {len(product_map)} products synced.")

                # === STEP 5: Price Variants ===
                self.stdout.write("💰 Creating price variants...")
                default_prices = {
                    'Adult': 9.00, 'Child': 5.00, 'OAP': 3.00,
                    'Student': 4.00, 'Infant': 0.00,
                }
                created = 0
                for product in product_map.values():
                    for code, price in default_prices.items():
                        # let Django auto PK here, variants don't have a remote ID
                        PriceVariant.objects.create(
                            product=product,
                            variant=code,
                            price=price
                        )
                        created += 1
                self.stdout.write(f"✅ {created} variants created.")

                # === STEP 6: Orders ===
                self.stdout.write("📄 Importing orders...")
                cursor.execute("""
                    SELECT wc_order_id, customer_id, session_id, session_date, booking_date,
                           num_adults, num_children, num_senior, num_under3,
                           adult_price, child_price, senior_price, under3_price, paid
                    FROM mor_generic_bookings
                    WHERE booking_date > '2023-11-25 12:16:17'
                      AND wc_order_id IS NOT NULL
                """)
                rows = cursor.fetchall()

                imported, skipped, errors = 0, 0, 0
                missing_users, missing_products = 0, 0

                for row in rows:
                    try:
                        user = User.objects.filter(id=row['customer_id']).first()
                        if not user:
                            missing_users += 1
                            continue

                        product = product_map.get(row['session_id'])
                        if not product:
                            missing_products += 1
                            continue

                        booking_date = row['session_date']
                        if isinstance(booking_date, str):
                            booking_date = datetime.strptime(booking_date, '%Y-%m-%d').date()

                        order, created = Order.objects.update_or_create(
                            id=row['wc_order_id'],  # force PK from remote
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
                            skipped += 1
                            continue

                        total = decimal.Decimal("0.00")
                        for label, qty in {
                            'Adult': row['num_adults'],
                            'Child': row['num_children'],
                            'OAP': row['num_senior'],
                            'Infant': row['num_under3'],
                        }.items():
                            if qty and qty > 0:
                                variant = PriceVariant.objects.filter(product=product, variant=label).first()
                                if variant:
                                    OrderItem.objects.create(
                                        order=order,
                                        variant=variant,
                                        quantity=qty
                                    )
                                    total += decimal.Decimal(variant.price) * qty

                        order.amount = total
                        order.save()
                        imported += 1

                    except Exception as e:
                        errors += 1
                        self.stderr.write(f"❌ Error importing order {row['wc_order_id']}: {e}")

                self.stdout.write(f"✅ Imported {imported} orders.")
                self.stdout.write(f"⏩ Skipped {skipped}, ❌ Errors: {errors}")
                self.stdout.write(f"⚠️  Missing users: {missing_users}, missing products: {missing_products}")

        finally:
            conn.close()
            self.stdout.write("🔒 Remote DB connection closed.")
