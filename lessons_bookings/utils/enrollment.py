from lessons_orders.models import Order, OrderItem
from lessons_bookings.models import LessonEnrollment


def handle_lessons_enrollment(order):
    # Retrieve relevant order items
    order_items = OrderItem.objects.filter(order=order)

    # Create LessonsEnrollment records for each order item
    for order_item in order_items:
        swimling = order_item.swimling
        lesson = order_item.product
        term = order_item.term

        # Create LessonsEnrollment record for the current order item
        LessonEnrollment.objects.create(
            swimling=swimling,
            lesson=lesson,
            term=term,
            # Other relevant fields
        )
