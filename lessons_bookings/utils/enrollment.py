import logging

from django.db import transaction
from lessons_orders.models import Order, OrderItem
from lessons_bookings.models import LessonEnrollment
from waiting_list.models import WaitingList


logger = logging.getLogger(__name__)

def handle_lessons_enrollment(order):
    # print( 'lesson_enrollment')
    try:
        with transaction.atomic():  # Ensures atomicity of the database operations
            # Retrieve relevant order items
            order_items = OrderItem.objects.filter(order=order)

            # Create LessonEnrollment records for each order item
            for order_item in order_items:
                swimling = order_item.swimling
                lesson = order_item.product
                term = order_item.term

                if term is None:
                    raise ValueError(
                        f"Order item {order_item.id} (order {order.id}) is missing a term; cannot create enrollment."
                    )

                # Create LessonEnrollment record for the current order item
                LessonEnrollment.objects.create(
                    swimling=swimling,
                    lesson=lesson,
                    term=term,
                    order=order,  # Include the order object
                    # Other relevant fields, e.g., notes=order_item.notes (if applicable)
                )
                # ✅ Mark waiting list entry as completed
                WaitingList.objects.filter(
                    swimling=swimling,
                    assigned_lesson=lesson,
                    completed=False
                ).update(completed=True)
        # Optional: Further actions upon successful enrollment (e.g., sending confirmation emails)

    except Exception:
        logger.exception("Error handling lessons enrollment for order %s", getattr(order, 'id', '?'))
        raise
