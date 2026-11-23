import logging

from django.db import transaction
from lessons_orders.models import Order, OrderItem
from lessons_bookings.models import LessonEnrollment
from waiting_list.models import WaitingList


logger = logging.getLogger(__name__)


def already_enrolled(swimling, lesson, term):
    """True if this swimling already holds a place in this class for this term.

    Booking it again takes a second payment for a place the database refuses to
    create (unique swimling+lesson+term). Four term-62 customers paid twice this
    way before the check existed (Nov 2026)."""
    if swimling is None or lesson is None or term is None:
        return False
    return LessonEnrollment.objects.filter(swimling=swimling, lesson=lesson, term=term).exists()


def already_enrolled_items(order):
    """The order's items whose swimling is already enrolled in that class and term."""
    return [item for item in OrderItem.objects.filter(order=order).select_related('swimling', 'product', 'term')
            if already_enrolled(item.swimling, item.product, item.term)]

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
