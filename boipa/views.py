from decimal import Decimal
import logging
import requests
from django.shortcuts import render, redirect
from django.http import HttpResponse, QueryDict
from django.urls import reverse
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import (
    SwimOrderPaymentNotification, LessonOrderPaymentNotification, SchoolOrderPaymentNotification,
    SwimOrder, LessonOrder, SchoolOrder
)
from lessons_bookings.utils.enrollment import handle_lessons_enrollment
from schools_bookings.utils.enrollment import handle_schools_enrollment
from .payment_functions import get_boipa_session_token  # External function
# Initialize logging
payments_logger = logging.getLogger('payments')


def initiate_boipa_payment_session(request, order_ref, total_price):
    """
    Initiates a payment session for BOIPA with the given order reference and total price.
    Redirects to the BOIPA Hosted Payment Page (HPP) if successful.
    """
    total_price = Decimal(total_price)
    token = get_boipa_session_token(request, order_ref, total_price)
    if token is None:
        payments_logger.error(f"Failed to obtain session token for order_ref {order_ref}")
        return render(request, 'error.html', {'error': 'Unable to obtain session token.'})

    hpp_url = f"{settings.HPP_FORM}?token={token}&merchantId={settings.BOIPA_MERCHANT_ID}&integrationMode=Standalone"
    return redirect(hpp_url)


def payment_response(request):
    payments_logger.debug(f"Received payment response: {request.GET.dict()}")
    result = request.GET.get('result')
    merchantTxId = request.GET.get('merchantTxId')
    if result == "success":
        return render(request, 'payment_success.html', {'order_ref': merchantTxId, 'message': result})
    elif result == "failure":
        return render(request, 'payment_failure.html', {'order_ref': merchantTxId, 'message': result})
    return render(request, 'error.html', {'error_message': 'Unknown payment response.'})


from django.http import JsonResponse


@csrf_exempt
def payment_notification(request):
    payments_logger.debug(f"Received payment Notification: {request.POST.dict()}")
    if request.method != 'POST':
        return HttpResponse("Invalid request method", status=405)

    data = QueryDict(request.body)
    merchantTxId = data.get('merchantTxId')
    if not merchantTxId:
        return HttpResponse("Missing merchantTxId", status=400)

    try:
        source_prefix, order_id_str = merchantTxId.split("_", 1)
        order_id = int(order_id_str)
    except (ValueError, IndexError):
        return HttpResponse("Invalid merchantTxId format", status=400)

    model_map = {
        'swims': (SwimOrder, SwimOrderPaymentNotification),
        'lesson': (LessonOrder, LessonOrderPaymentNotification, handle_lessons_enrollment),
        'school': (SchoolOrder, SchoolOrderPaymentNotification, handle_schools_enrollment),
    }

    if source_prefix in model_map:
        OrderModel, NotificationModel, enrollment_func = model_map[source_prefix]
        try:
            with transaction.atomic():
                order = OrderModel.objects.get(id=order_id)
                order.paid = True
                order.txId = data.get('txId', '')
                order.save()

                notification = NotificationModel.objects.create(
                    order=order,
                    txId=data.get('txId', ''),
                    merchantTxId=data.get('merchantTxId', ''),
                    country=data.get('country', ''),
                    amount=data.get('amount', None),
                    currency=data.get('currency', ''),
                    action=data.get('action', ''),
                    auth_code=data.get('auth_code', ''),
                    acquirer=data.get('acquirer', ''),
                    acquirerAmount=data.get('acquirerAmount', None),
                    merchantId=data.get('merchantId', ''),
                    brandId=data.get('brandId', ''),
                    customerId=data.get('customerId', ''),
                    acquirerCurrency=data.get('acquirerCurrency', ''),
                    paymentSolutionId=data.get('paymentSolutionId', None),
                    status=data.get('status', '')
                )

                # Call the enrollment function if the order is paid successfully
                enrollment_func(order)

                return HttpResponse('Payment processed successfully', status=200)
        except OrderModel.DoesNotExist:
            return HttpResponse("Order not found", status=404)
        except Exception as e:
            return HttpResponse(f"Error processing payment: {str(e)}", status=500)

    return HttpResponse("Source prefix not recognized", status=400)
