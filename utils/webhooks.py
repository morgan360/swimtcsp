import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from lessons_orders.models import Order as LessonsOrder
from swims_orders.models import Order as SwimsOrder
from lessons_bookings.utils.enrollment import handle_lessons_enrollment  #
from django.contrib.auth import get_user_model
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET)
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    if event.type == 'checkout.session.completed':
        session = event.data.object
        if session.mode == 'payment' and session.payment_status == 'paid':
            order_type = session.metadata.get('order_type')
            if order_type == 'lessons':
                try:
                    order = LessonsOrder.objects.get(
                        id=session.client_reference_id)
                except LessonsOrder.DoesNotExist:
                    return HttpResponse(status=404)

                # Update order as paid
                order.paid = True
                order.stripe_id = session.payment_intent
                order.save()
                send_order_confirmation_email(order)
                # Call the function in lessons_booking to handle lesson
                # enrollment
                handle_lessons_enrollment(order)
                # Send order confirmation email to the user


            elif order_type == 'swims':
                try:
                    order = SwimsOrder.objects.get(
                        id=session.client_reference_id)
                except SwimsOrder.DoesNotExist:
                    return HttpResponse(status=404)

                # Update order as paid
                order.paid = True
                order.stripe_id = session.payment_intent
                order.save()

            # ... Other order_type handling ...

    return HttpResponse(status=200)


def send_order_confirmation_email(order):
    subject = 'Order Confirmation'
    message = 'Thank you for your order!'
    from_email = 'morgan.mcknightr@gmail.com'
    recipient_list = [order.user.email]

    # Render the HTML template for the email
    html_message = render_to_string('emails/order_confirmation.html',
                                    {'order': order})
    # send_mail(subject, message, from_email, recipient_list, html_message=html_message)

    # Send the email
    send_mail(
        subject,
        '',  # Use an empty string for the plain text content
        from_email,
        recipient_list,  # To email addresses (recipient's email)
        html_message=html_message,
    )
