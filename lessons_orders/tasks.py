from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import Order, OrderItem


def send_lesson_order_email(order_id):
    try:
        order = Order.objects.get(id=order_id)
        order_items = order.items.all()
    except Order.DoesNotExist:
        return False

    subject = f"📘 TCSP Lesson Booking Confirmation — Order #{order.id}"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [order.user.email]

    # Calculate total
    total_price = sum(item.get_cost() for item in order_items)

    context = {
        "user": order.user,
        "order": order,
        "order_items": order_items,
        "total_price": order.amount,  # ✅ already discounted
        "coupon": order.coupon,
        "discount": order.discount_amount,
        "original_price": order.amount + (order.discount_amount or 0),  # Optional
        "support_email": settings.DEFAULT_FROM_EMAIL,
    }

    text_body = render_to_string("emails/lesson_order_confirmation.txt", context)
    html_body = render_to_string("emails/lesson_order_confirmation.html", context)

    msg = EmailMultiAlternatives(subject, text_body, from_email, to_email)
    msg.attach_alternative(html_body, "text/html")
    msg.send()

    return True
