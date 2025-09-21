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
    SwimOrder, LessonOrder, SchoolOrder)
from lessons_bookings.utils.enrollment import handle_lessons_enrollment
from schools_bookings.utils.enrollment import handle_schools_enrollment
from .payment_functions import get_boipa_session_token  # External function
from swims_orders.tasks import send_order_email
from lessons_orders.tasks import send_lesson_order_email
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse


# Initialize logging
boipa_logger = logging.getLogger("boipa")


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
    boipa_logger = logging.getLogger("boipa")
    boipa_logger.debug(f"Received payment response: {request.GET.dict()}")

    result = request.GET.get("result")
    merchantTxId = request.GET.get("merchantTxId")

    order_ref = None
    if merchantTxId:
        parts = merchantTxId.split("_")
        if len(parts) >= 2:
            try:
                order_ref = int(parts[1])  # ✅ only second part is numeric ID
            except ValueError:
                order_ref = merchantTxId  # fallback to raw if parsing fails

    context = {
        "order_ref": order_ref,
        "merchantTxId": merchantTxId,  # optional, for debugging/logging
        "message": result,
    }

    if result == "success":
        return render(request, "boipa/payment_success.html", context)
    elif result == "failure":
        return render(request, "boipa/payment_failure.html", context)
    return render(request, "boipa/error.html", {"error_message": "Unknown payment response."})

@csrf_exempt
def payment_notification(request):
    boipa_logger.debug("📥 payment_notification view triggered")

    # 🔎 Raw request info
    boipa_logger.debug(f"🔎 RAW PATH: {request.get_full_path()}")
    boipa_logger.debug(f"🔎 QUERY STRING: {request.META.get('QUERY_STRING')}")
    boipa_logger.debug(f"🔎 HEADERS: {dict(request.headers)}")
    try:
        raw_body = request.body.decode("utf-8")
    except Exception:
        raw_body = "<unable to decode>"
    boipa_logger.debug(f"🔎 RAW BODY: {raw_body}")

    # Parse GET/POST
    if request.method == "POST":
        data = request.POST
    elif request.method == "GET":
        data = request.GET
    else:
        boipa_logger.error(f"❌ Invalid request method: {request.method}")
        return HttpResponse("Invalid request method", status=405)

    boipa_logger.debug(f"📦 Parsed notification data: {data.dict()}")

    merchantTxId = data.get("merchantTxId")
    if not merchantTxId:
        boipa_logger.error("❌ merchantTxId missing from payload")
        return HttpResponse("Missing merchantTxId", status=400)

    # Parse merchantTxId into prefix + numeric order_id
    parts = merchantTxId.split("_")
    if len(parts) < 2:
        boipa_logger.error(f"❌ Invalid merchantTxId format: {merchantTxId}")
        return HttpResponse("Invalid merchantTxId format", status=400)

    source_prefix = parts[0]
    try:
        order_id = int(parts[1])
    except ValueError:
        boipa_logger.error(f"❌ Could not parse order_id from {parts[1]}")
        return HttpResponse("Invalid order_id", status=400)

    boipa_logger.debug(
        f"🔍 Extracted source_prefix={source_prefix}, order_id={order_id}, full merchantTxId={merchantTxId}"
    )

    # --- Models mapping ---
    def noop(order):
        return

    model_map = {
        "swims": (SwimOrder, SwimOrderPaymentNotification, noop),
        "lesson": (LessonOrder, LessonOrderPaymentNotification, handle_lessons_enrollment),
        "school": (SchoolOrder, SchoolOrderPaymentNotification, handle_schools_enrollment),
    }

    if source_prefix not in model_map:
        boipa_logger.error(f"❌ Source prefix '{source_prefix}' not recognized")
        return HttpResponse("Source prefix not recognized", status=400)

    OrderModel, NotificationModel, enrollment_func = model_map[source_prefix]

    try:
        with transaction.atomic():
            order = OrderModel.objects.get(id=order_id)

            result = data.get("result")
            status = data.get("status")

            # ✅ Only mark as paid if BOIPA confirms
            if result == "success" or status == "CAPTURED":
                boipa_logger.debug(f"Marking order {order.id} as paid (result={result}, status={status})")
                order.paid = True
                order.txId = data.get("txId", "")
                order.paid = True
                order.txId = data.get("txId", "")
                order.save()
                boipa_logger.debug(f"✅ Order saved in DB: id={order.id}, paid={order.paid}, txId={order.txId}")
            else:
                boipa_logger.warning(
                    f"Payment not marked as paid for order {order.id}: result={result}, status={status}"
                )
                return HttpResponse("Payment not successful", status=200)

            # ✅ Create notification record
            NotificationModel.objects.create(
                order=order,
                txId=data.get("txId", ""),
                merchantTxId=merchantTxId,
                country=data.get("country", ""),
                amount=data.get("amount", None),
                currency=data.get("currency", ""),
                action=data.get("action", ""),
                auth_code=data.get("auth_code", ""),
                acquirer=data.get("acquirer", ""),
                acquirerAmount=data.get("acquirerAmount", None),
                merchantId=data.get("merchantId", ""),
                brandId=data.get("brandId", ""),
                customerId=data.get("customerId", ""),
                acquirerCurrency=data.get("acquirerCurrency", ""),
                paymentSolutionId=data.get("paymentSolutionId", None),
                status=status or "",
                errorMessage=data.get("errorMessage", "No error message provided"),
            )
            boipa_logger.info(f"📝 Payment notification record created for order {order.id}")

            # ✅ Enrollment / follow-up actions
            enrollment_func(order)
            boipa_logger.debug(f"📚 Enrollment function called for order {order.id}")

            # ✅ Send emails last
            if source_prefix == "swims":
                boipa_logger.debug(f"📧 Sending swim order email for order {order.id}")
                send_order_email(order.id)
            elif source_prefix == "lesson":
                boipa_logger.debug(f"📨 Sending lesson order email for order {order.id}")
                send_lesson_order_email(order.id)

            return HttpResponse("Payment processed successfully", status=200)

    except OrderModel.DoesNotExist:
        boipa_logger.error(f"❌ Order {order_id} not found in {OrderModel.__name__}")
        return HttpResponse("Order not found", status=404)
    except Exception as e:
        boipa_logger.exception(f"❌ Exception during processing: {e}")
        return HttpResponse(f"Error processing payment: {str(e)}", status=500)

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