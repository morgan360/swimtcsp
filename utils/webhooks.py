import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from lessons_orders.models import Order as LessonsOrder
from swims_orders.models import Order as SwimsOrder
from lessons_bookings.context_processors import current_term


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
                except Order.DoesNotExist:
                    return HttpResponse(status=404)

                # Update order as paid
                order.paid = True
                order.stripe_id = session.payment_intent

                # Call the context processor to get current term
                context = {}
                current_term(context)
                current_term_id = context['current_term'].term_id

                # Store the current_term_id in the Order object
                order.term_id = current_term_id
                order.save()

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
