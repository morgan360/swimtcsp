from django.db import transaction
from schools_orders.models import Order, OrderItem
from schools_bookings.models import ScoEnrollment

def handle_schools_enrollment(order):
    print(f"[Schools Enrollment] Processing order ID: {order.id}")

    try:
        with transaction.atomic():
            order_items = OrderItem.objects.filter(order=order)

            for item in order_items:
                swimling = item.swimling
                lesson = item.product
                term = item.term

                if not all([swimling, lesson, term]):
                    print(f"[Warning] Skipping item {item.id} due to missing data.")
                    continue

                enrollment, created = ScoEnrollment.objects.get_or_create(
                    swimling=swimling,
                    lesson=lesson,
                    term=term,
                    defaults={
                        'order': order,
                        # Add other default fields here if needed, e.g., 'notes': item.notes
                    }
                )

                if created:
                    print(f"[Success] Enrolled {swimling} in lesson {lesson} for term {term}.")
                else:
                    print(f"[Info] Enrollment already exists for {swimling} (item {item.id}).")

    except Exception as e:
        print(f"[Error] Failed to process schools enrollment: {str(e)}")
        # Optionally: raise or log to Sentry, etc.
