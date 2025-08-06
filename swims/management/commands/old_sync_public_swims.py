import pymysql
from datetime import time, timedelta
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from swims.models import PublicSwimCategory, PublicSwimProduct, PriceVariant
from decouple import config

DAY_CHOICES = {
    0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday',
    4: 'Friday', 5: 'Saturday', 6: 'Sunday'
}

def safe_time(val):
    """Normalize time object to avoid duplication due to second/microsecond precision."""
    if isinstance(val, time):
        return val.replace(second=0, microsecond=0)
    if isinstance(val, timedelta):
        total_seconds = int(val.total_seconds())
        return time(hour=(total_seconds // 3600) % 24, minute=(total_seconds % 3600) // 60)
    return None

class Command(BaseCommand):
    help = "Sync Public Swim categories, products, and price variants from remote DB"

    def handle(self, *args, **options):
        from swims_orders.models import Order, OrderItem
        from swims.models import PublicSwimCategory, PublicSwimProduct, PriceVariant
        from django.db import connection

        self.stdout.write("🧹 Deleting all public swim data...")

        # Delete in correct dependency order
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        PriceVariant.objects.all().delete()
        PublicSwimProduct.objects.all().delete()
        PublicSwimCategory.objects.all().delete()

        # Reset AUTO_INCREMENT for clean DB
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE swims_orders_orderitem AUTO_INCREMENT = 1;")
            cursor.execute("ALTER TABLE swims_orders_order AUTO_INCREMENT = 1;")
            cursor.execute("ALTER TABLE swims_pricevariant AUTO_INCREMENT = 1;")
            cursor.execute("ALTER TABLE swims_publicswimproduct AUTO_INCREMENT = 1;")
            cursor.execute("ALTER TABLE swims_publicswimcategory AUTO_INCREMENT = 1;")

        self.stdout.write("🧼 Tables cleared and reset.")
        self.stdout.write("\U0001F310 Connecting to remote database...")
        conn = pymysql.connect(
            host=config('REMOTE_TCSP_DB_HOST'),
            port=config('REMOTE_TCSP_DB_PORT', cast=int),
            user=config('REMOTE_TCSP_DB_USER'),
            password=config('REMOTE_TCSP_DB_PASSWORD'),
            database=config('REMOTE_TCSP_DB_NAME'),
            charset=config('REMOTE_TCSP_DB_CHARSET'),
            cursorclass=pymysql.cursors.DictCursor
        )

        try:
            with conn.cursor() as cursor:
                # STEP 1: Categories
                self.stdout.write("🔹 Importing Public Swim Categories...")
                cursor.execute("SELECT id, event FROM mor_events")
                events = cursor.fetchall()
                event_map = {}
                for e in events:
                    cat, _ = PublicSwimCategory.objects.get_or_create(
                        slug=slugify(e['event']),
                        defaults={'name': e['event'], 'description': ''}
                    )
                    event_map[e['id']] = cat
                self.stdout.write(f"✅ {len(event_map)} categories synced.")

                # STEP 2: Products
                self.stdout.write("🔹 Importing Public Swim Products...")
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
                    end_time = safe_time(s['time_end'])

                    time_str = start_time.strftime('%H%M') if start_time else '0000'
                    slug = slugify(f"{category.slug}-{s['day_id']}-{time_str}")
                    name = f"{category.name} ({DAY_CHOICES.get(s['day_id'], 'Unknown')} {time_str})"

                    try:
                        product = PublicSwimProduct.objects.get(external_id=s['id'])
                        updated = False

                        if product.slug != slug:
                            product.slug = slug
                            updated = True

                        product.name = name
                        product.category = category
                        product.start_time = start_time
                        product.end_time = end_time
                        product.day_of_week = s['day_id']
                        product.num_places = s['num_places']
                        product.available = bool(s['active'])
                        product.save()

                        product_map[s['id']] = product
                        status = "↻ Updated"
                        self.stdout.write(f"{status}: {slug} (ID: {product.id})")

                    except PublicSwimProduct.DoesNotExist:
                        # Fallback: look for existing product by slug
                        existing = PublicSwimProduct.objects.filter(slug=slug).first()
                        if existing:
                            existing.external_id = s['id']
                            existing.name = name
                            existing.category = category
                            existing.start_time = start_time
                            existing.end_time = end_time
                            existing.day_of_week = s['day_id']
                            existing.num_places = s['num_places']
                            existing.available = bool(s['active'])
                            existing.save()
                            product_map[s['id']] = existing
                            self.stdout.write(f"🔗 Linked existing: {slug} → external_id {s['id']}")
                        else:
                            product = PublicSwimProduct.objects.create(
                                external_id=s['id'],
                                slug=slug,
                                name=name,
                                category=category,
                                start_time=start_time,
                                end_time=end_time,
                                day_of_week=s['day_id'],
                                num_places=s['num_places'],
                                available=bool(s['active'])
                            )
                            product_map[s['id']] = product
                            self.stdout.write(f"🆕 Created: {slug} (ID: {product.id})")

                    except Exception as e:
                        self.stdout.write(f"❌ Error syncing product ID {s['id']}: {e}")

                self.stdout.write(f"✅ {len(product_map)} products synced.")

                # STEP 3: Price Variants
                self.stdout.write("🔹 Creating placeholder Price Variants...")
                created_count = 0
                skipped_count = 0

                for product in product_map.values():
                    for code, _ in PriceVariant.VARIANT_CHOICES:
                        normalized_code = code.strip().title()
                        default_prices = {
                            'Adult': 9.00,
                            'Child': 5.00,
                            'OAP': 3.00,
                            'Student': 4.00,
                            'Infant': 0.00,
                        }

                        # Inside your loop
                        price = default_prices.get(normalized_code, 0.00)
                        obj, created = PriceVariant.objects.get_or_create(
                            product=product,
                            variant=normalized_code,
                            defaults={'price': price}
                        )
                        if created:
                            created_count += 1
                        else:
                            skipped_count += 1

                self.stdout.write(f"✅ {created_count} new price variants created.")
                self.stdout.write(f"ℹ️  {skipped_count} variants already existed.")

        finally:
            conn.close()
            self.stdout.write("🔒 Connection closed.")
