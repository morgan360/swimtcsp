from decimal import Decimal
import logging
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from coupons.models import CouponRedemption
from .models import Order

logger = logging.getLogger("orders")

def _as_decimal(value, default="0"):
    """Safely convert a value (tuple, list, None, str, int, Decimal) to Decimal."""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else default
    if value is None:
        value = default
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)

def send_lesson_order_email(order_id):
    try:
        order = Order.objects.get(id=order_id)
        order_items = order.items.all()
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found — email not sent.")
        return False

    subject = f"📘 TCSP Lesson Booking Confirmation — Order #{order.id}"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [order.user.email]

    # --- Safe arithmetic for totals ---
    amount = _as_decimal(order.amount)
    original_price = _as_decimal(order.get_total_cost())
    discount = original_price - amount

    redemptions = list(
        CouponRedemption.objects.filter(
            content_type=ContentType.objects.get_for_model(Order),
            object_id=order.id,
        ).select_related('coupon')
    )

    context = {
        "user": order.user,
        "order": order,
        "order_items": order_items,
        "total_price": amount,            # discounted total
        "redemptions": redemptions,       # one row per applied coupon
        "discount": discount,             # total discount across all coupons
        "original_price": original_price, # pre-discount subtotal
        "support_email": settings.DEFAULT_SUPPORT_EMAIL,
    }

    try:
        text_body = render_to_string("emails/lesson_order_confirmation.txt", context)
        html_body = render_to_string("emails/lesson_order_confirmation.html", context)

        msg = EmailMultiAlternatives(subject, text_body, from_email, to_email)
        msg.attach_alternative(html_body, "text/html")
        msg.send()
        logger.info(f"Lesson order confirmation sent for order {order.id}")
        return True

    except Exception as e:
        logger.exception(f"Error sending lesson order email for order {order.id}: {e}")
        return False
