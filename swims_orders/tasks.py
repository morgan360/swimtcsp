from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from swims_orders.models import Order  # adjust if located elsewhere


def send_order_email(order_id):
    """
    Sends a confirmation email with HTML content to the user
    after a successful swim booking.
    """
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return False

    subject = f"🏊 TCSP Booking Confirmation — Order #{order.id}"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [order.user.email]

    context = {
        "user": order.user,
        "order": order,
        "product": order.product,
        "booking_date": order.booking,
    }

    # Render both plain text and HTML templates
    text_body = render_to_string("emails/order_confirmation.txt", context)
    html_body = render_to_string("emails/order_confirmation.html", context)

    msg = EmailMultiAlternatives(subject, text_body, from_email, to_email)
    msg.attach_alternative(html_body, "text/html")
    msg.send()

    return True
