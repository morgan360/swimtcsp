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
    # Retrieve the payload and the Stripe signature from the request
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        # Construct the event object by verifying the webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError as e:
        # Handle the exception if the payload is invalid
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Handle the exception if the signature verification fails
        return HttpResponse(status=400)

    # Check if the webhook event is of type 'checkout.session.completed'
    if event.type == 'checkout.session.completed':
        session = event.data.object  # Extract the session object from the event

        # Check if the session is for a payment and the payment status is 'paid'
        if session.mode == 'payment' and session.payment_status == 'paid':
            order_type = session.metadata.get('order_type')  # Retrieve the order type from metadata

            # Handle 'lessons' order type
            if order_type == 'lessons':
                try:
                    # Retrieve the corresponding LessonsOrder object
                    order = LessonsOrder.objects.get(id=session.client_reference_id)
                except LessonsOrder.DoesNotExist:
                    # Return a 404 response if the order does not exist
                    return HttpResponse(status=404)

                # Update the order status to paid and save the Stripe ID
                order.paid = True
                order.stripe_id = session.payment_intent
                order.save()

                # Specify the email template to use for order confirmation
                template = 'emails/lessons_order_confirmation.html'
                # Send an order confirmation email to the customer
                send_order_confirmation_email(order, template)

                # Call a function to handle lesson enrollment based on the order
                handle_lessons_enrollment(order)

            # Handle 'swims' order type
            elif order_type == 'swims':
                try:
                    # Retrieve the corresponding SwimsOrder object
                    order = SwimsOrder.objects.get(id=session.client_reference_id)
                except SwimsOrder.DoesNotExist:
                    # Return a 404 response if the order does not exist
                    return HttpResponse(status=404)

                # Update the order status to paid and save the Stripe ID
                order.paid = True
                order.stripe_id = session.payment_intent
                order.save()

                # Specify the email template for swims order confirmation
                template = 'emails/swims_order_confirmation.html'
                # Send an order confirmation email for the swims order
                send_order_confirmation_email(order, template)

            # ... Additional handling for other order types can be added here ...

    # Return a 200 HTTP response to indicate successful processing of the webhook
    return HttpResponse(status=200)

# Function to send an order confirmation email
def send_order_confirmation_email(order, template):
    # Define the email subject and message body
    subject = f'Order Confirmation for Order #{order.id}'
    message = f'Thank you for your order. Your order #{order.id} has been received.'

    # Sender's email address
    from_email = settings.FROM_EMAIL
    # Recipient list - in this case, the order user's email
    recipient_list = [order.user.email]

    # Render the HTML content for the email using the specified template
    html_message = render_to_string(template, {'order': order})

    # Send the email with both plain text and HTML content
    send_mail(
        subject,
        message,  # Plain text content
        from_email,
        recipient_list,  # Recipient's email address
        html_message=html_message,  # HTML content
    )
