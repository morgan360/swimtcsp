from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from schools_orders.models import Order

def send_school_order_email(order_id):
    import sys
    print(f"📧 EMAIL FUNCTION TRIGGERED for order {order_id}", file=sys.stderr)

    try:
        order = Order.objects.get(id=order_id)
        first_item = order.items.first()
    except Order.DoesNotExist:
        return
    except AttributeError:
        return  # Safeguard if no items exist

    if not first_item:
        return  # No items attached to the order

    subject = f"📘 TCSP School Booking Confirmation — Order #{order.id}"
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [order.user.email]

    context = {
        "user": order.user,
        "swimling": first_item.swimling,
        "lesson": first_item.product,
        "term": first_item.term,
        "school": order.school,
        "coupon": order.coupon,
        "discount": order.discount_amount,
        "support_email": settings.DEFAULT_SUPPORT_EMAIL,
    }

    text_body = render_to_string("emails/school_booking.txt", context)
    html_body = render_to_string("emails/school_booking.html", context)

    msg = EmailMultiAlternatives(subject, text_body, from_email, to_email)
    msg.attach_alternative(html_body, "text/html")
    print("📧 Email DEBUG:")
    print("  FROM:", from_email)
    print("  TO:", to_email)
    print("  SUBJECT:", subject)
    print("  TEXT BODY:", text_body)
    print("  HTML BODY:", html_body)

    try:
        msg.send()
        print(f"✅ Email sent successfully to {to_email}")
    except Exception as e:
        print(f"❌ Email failed to send: {e}")

