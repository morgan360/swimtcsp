# from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from swims_orders.models import Order  # adjust if your Order model is elsewhere

# @shared_task
def send_order_email(order_id):
    """
    Task to send an email confirmation to the user
    after successfully placing a swim order.
    """
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return False  # You could also log this error

    subject = f"🏊 TCSP Swim Booking Confirmation - Order #{order.id}"

    message = (
        f"Dear {order.user.first_name},\n\n"
        f"Thank you for booking a swim session with TCSP.\n"
        f"Your order ID is {order.id} and your booking is confirmed.\n\n"
        f"If you have any questions, feel free to contact us at {settings.DEFAULT_FROM_EMAIL}.\n\n"
        f"Best regards,\n"
        f"TCSP Swim Team"
    )

    return send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [order.user.email],
        fail_silently=False,
    )
