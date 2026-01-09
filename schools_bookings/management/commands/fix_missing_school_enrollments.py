"""
Management command to fix missing school enrollments for paid orders.

This command finds all paid school orders that don't have corresponding
enrollments and creates them using the handle_schools_enrollment function.

Usage:
    python manage.py fix_missing_school_enrollments [--dry-run]
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from schools_orders.models import Order as SchoolOrder
from schools_bookings.models import ScoEnrollment
from schools_bookings.utils.enrollment import handle_schools_enrollment


class Command(BaseCommand):
    help = 'Fix missing school enrollments for paid orders'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))

        # Find all paid school orders
        paid_orders = SchoolOrder.objects.filter(paid=True).order_by('id')

        self.stdout.write(f"\nFound {paid_orders.count()} paid school orders")

        orders_with_missing_enrollments = []

        for order in paid_orders:
            # Check if this order has enrollments
            enrollment_count = ScoEnrollment.objects.filter(order=order).count()
            order_items_count = order.items.count()

            if enrollment_count == 0 and order_items_count > 0:
                orders_with_missing_enrollments.append(order)
                self.stdout.write(
                    self.style.WARNING(
                        f"\nOrder #{order.id} (txId: {order.txId})"
                        f"\n  - Has {order_items_count} order items"
                        f"\n  - Has {enrollment_count} enrollments"
                        f"\n  - Created: {order.created}"
                    )
                )

                # Show order items
                for item in order.items.all():
                    self.stdout.write(
                        f"    • {item.swimling} → {item.product} (Term: {item.term})"
                    )

        if not orders_with_missing_enrollments:
            self.stdout.write(self.style.SUCCESS('\n✅ No orders with missing enrollments found!'))
            return

        self.stdout.write(
            self.style.WARNING(
                f"\n\nFound {len(orders_with_missing_enrollments)} orders with missing enrollments"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    '\nDry run complete. Run without --dry-run to fix these orders.'
                )
            )
            return

        # Fix the orders
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Starting enrollment creation...\n')

        success_count = 0
        error_count = 0

        for order in orders_with_missing_enrollments:
            try:
                self.stdout.write(f"\nProcessing Order #{order.id}...")
                handle_schools_enrollment(order)

                # Verify enrollments were created
                new_enrollment_count = ScoEnrollment.objects.filter(order=order).count()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Order #{order.id}: Created {new_enrollment_count} enrollments"
                    )
                )
                success_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ Order #{order.id}: Failed - {str(e)}"
                    )
                )
                error_count += 1

        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully fixed: {success_count} orders'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ Failed: {error_count} orders'))
        self.stdout.write('\nDone!\n')