from django.db import transaction
from lessons_orders.models import Order, OrderItem
from lessons_bookings.models import LessonEnrollment
from waiting_list.models import WaitingList

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

    except Exception as e:
        # Handle exceptions (e.g., invalid data, database errors)
        print(f"Error handling lessons enrollment: {str(e)}")
        # Optionally, re-raise the exception or handle it as per your application's error handling strategy
