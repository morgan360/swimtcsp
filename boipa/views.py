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
from swims_orders.tasks import send_order_email
from lessons_orders.tasks import send_lesson_order_email
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse


# Initialize logging
payments_logger = logging.getLogger('payments')


def initiate_boipa_payment_session(request, order_ref, total_price):
    total_price = Decimal(total_price)

    # 🔁 Allow switching between 'Iframe' and 'Standalone' via query param
    integration_mode = request.GET.get('mode', 'Standalone').capitalize()
    if integration_mode not in ['Standalone', 'Iframe']:
        integration_mode = 'Standalone'

    token = get_boipa_session_token(request, order_ref, total_price)
    if token is None:
        payments_logger.error(f"Failed to obtain session token for order_ref {order_ref}")
        return render(request, 'boipa/error.html', {'error': 'Unable to obtain session token.'})

    hpp_url = (
        f"{settings.HPP_FORM}?token={token}"
        f"&merchantId={settings.BOIPA_MERCHANT_ID}"
        f"&integrationMode={integration_mode}"
    )

    # Render iframe page or redirect based on mode
    if integration_mode == 'Iframe':
        return render(request, 'boipa/payment_form.html', {'hpp_url': hpp_url})
    else:
        return redirect(hpp_url)


def payment_response(request):
    payments_logger.debug(f"Received payment response: {request.GET.dict()}")
    result = request.GET.get('result')
    merchantTxId = request.GET.get('merchantTxId')
    if result == "success":
        return render(request, 'boipa/payment_success.html', {'order_ref': merchantTxId, 'message': result})
    elif result == "failure":
        return render(request, 'boipa/payment_failure.html', {'order_ref': merchantTxId, 'message': result})
    return render(request, 'boipa/error.html', {'error_message': 'Unknown payment response.'})

@csrf_exempt
def payment_notification(request):
    print("📥 payment_notification view triggered")
    payments_logger.debug(f"Received payment Notification ({request.method}): "
                          f"GET={request.GET.dict()} POST={request.POST.dict()}")

    # ✅ Accept both POST and GET
    if request.method == 'POST':
        data = request.POST
    elif request.method == 'GET':
        data = request.GET
    else:
        print("❌ Invalid request method:", request.method)
        return HttpResponse("Invalid request method", status=405)

    print("📦 Parsed notification data:", data.dict())

    merchantTxId = data.get('merchantTxId')
    if not merchantTxId:
        print("❌ merchantTxId missing from payload")
        return HttpResponse("Missing merchantTxId", status=400)

    try:
        parts = merchantTxId.split("_")
        source_prefix = parts[0]
        order_id = int(parts[1])
        print(f"🔍 Extracted source_prefix: {source_prefix}, order_id: {order_id}")
    except (ValueError, IndexError) as e:
        print(f"❌ Error parsing merchantTxId: {merchantTxId} → {e}")
        return HttpResponse("Invalid merchantTxId format", status=400)

    def noop(order): return

    model_map = {
        'swims': (SwimOrder, SwimOrderPaymentNotification, noop),
        'lesson': (LessonOrder, LessonOrderPaymentNotification, handle_lessons_enrollment),
        'school': (SchoolOrder, SchoolOrderPaymentNotification, handle_schools_enrollment),
    }

    print("🔑 Available source prefixes:", list(model_map.keys()))

    if source_prefix in model_map:
        OrderModel, NotificationModel, enrollment_func = model_map[source_prefix]
        try:
            print(f"📄 Looking up order with ID {order_id} from model {OrderModel.__name__}")
            with transaction.atomic():
                order = OrderModel.objects.get(id=order_id)
                order.paid = True
                order.txId = data.get('txId', '')
                order.save()
                print(f"✅ Order {order_id} marked as paid")

                # ✅ Explicit email dispatch based on type
                if source_prefix == 'swims':
                    print("📧 Sending swim order email")
                    send_order_email(order.id)
                elif source_prefix == 'lesson':
                    print("📨 Sending lesson order email")
                    send_lesson_order_email(order.id)

                NotificationModel.objects.create(
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
                    status=data.get('status', ''),
                    errorMessage=data.get('errorMessage', 'No error message provided'),
                )
                print("📝 Payment notification record created")

                enrollment_func(order)
                print("📚 Enrollment function called")

                return HttpResponse('Payment processed successfully', status=200)

        except OrderModel.DoesNotExist:
            print(f"❌ Order {order_id} not found in model {OrderModel.__name__}")
            return HttpResponse("Order not found", status=404)
        except Exception as e:
            print(f"❌ Exception during processing: {e}")
            return HttpResponse(f"Error processing payment: {str(e)}", status=500)

    print(f"❌ Source prefix '{source_prefix}' not recognized")
    return HttpResponse("Source prefix not recognized", status=400)


#### REFUND LOGIC ####
@staff_member_required
def refund_order_view(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        raise Http404("Order not found")

    if not order.paid:
        return JsonResponse({"error": "Cannot refund an unpaid order"}, status=400)

    result = refund_boipa_transaction(order.txId, order.amount)

    if result["success"]:
        order.payment_status = "refunded"
        order.save()
        return JsonResponse({"message": "Refund successful", "txId": order.txId})
    else:
        return JsonResponse({
            "error": "Refund failed",
            "boipa_response": result["data"]
        }, status=400)