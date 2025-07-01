from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from swims_orders.models import Order, OrderItem


def send_order_email(order_id):
    try:
        order = Order.objects.get(id=order_id)
        order_items = OrderItem.objects.filter(order=order)
    except Order.DoesNotExist:
        return False

    subject = f"🏊 TCSP Swim Booking Confirmation — Order #{order.id}"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [order.user.email]

    # Total calculation
    total_price = sum(item.variant.price * item.quantity for item in order_items)

    context = {
        "user": order.user,
        "order": order,
        "product": order.product,
        "booking_date": order.booking,
        "order_items": order_items,
        "total_price": total_price,
        "support_email": settings.DEFAULT_FROM_EMAIL
    }

    text_body = render_to_string("emails/order_confirmation.txt", context)
    html_body = render_to_string("emails/order_confirmation.html", context)

    msg = EmailMultiAlternatives(subject, text_body, from_email, to_email)
    msg.attach_alternative(html_body, "text/html")
    msg.send()

    return True
