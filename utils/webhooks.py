import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from lessons_orders.models import Order as LessonsOrder
from swims_orders.models import Order as SwimsOrder

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
                # Use the LessonsOrder model
                try:
                    order = LessonsOrder.objects.get(id=session.client_reference_id)
                except Order.DoesNotExist:
                    return HttpResponse(status=404)
            elif order_type == 'swims':
                try:
                    order = SwimsOrder.objects.get(
                        id=session.client_reference_id)
                except SwimsOrder.DoesNotExist:
                    return HttpResponse(status=404)
            else:
                return HttpResponse(status=400)  # Unknown order_type
                # Common handling logic for both order types
                # mark order as paid
            order.paid = True
            # store Stripe payment ID
            order.stripe_id = session.payment_intent
            order_type = session.metadata.get('order_type')
            order.save()
            # launch asynchronous task
        # payment_completed.delay(order.id)

    return HttpResponse(status=200)
