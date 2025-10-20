from decimal import Decimal
import logging
import requests
from django.shortcuts import render, redirect
from django.http import HttpResponse, QueryDict
from django.urls import reverse
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
from schools_orders.tasks import send_school_order_email
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from urllib.parse import parse_qs
from decimal import Decimal, InvalidOperation
from django.db import transaction, IntegrityError


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
    boipa_logger.debug(f"🔎 RAW PATH: {request.get_full_path()}")
    boipa_logger.debug(f"🔎 QUERY STRING: {request.META.get('QUERY_STRING')}")
    boipa_logger.debug(f"🔎 HEADERS: {dict(request.headers)}")

    try:
        raw_body = request.body.decode("utf-8")
    except Exception:
        raw_body = "<unable to decode>"
    boipa_logger.debug(f"🔎 RAW BODY: {raw_body}")

    # --- Parse incoming data ---
    if request.method == "POST":
        data = request.POST.dict()
        if not data and raw_body and raw_body != "<unable to decode>":
            try:
                parsed = parse_qs(raw_body)
                data = {k: v[0] for k, v in parsed.items()}
            except Exception as e:
                boipa_logger.error(f"❌ Failed to parse raw body manually: {e}")
    elif request.method == "GET":
        data = request.GET.dict()
    else:
        return HttpResponse("Invalid request method", status=405)

    boipa_logger.debug(f"📦 Parsed notification data: {data}")

    merchantTxId = data.get("merchantTxId")
    if not merchantTxId:
        boipa_logger.error("❌ merchantTxId missing from payload")
        return HttpResponse("Missing merchantTxId", status=400)

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

    model_map = {
        "swims": (SwimOrder, SwimOrderPaymentNotification, send_order_email, None),
        "lesson": (LessonOrder, LessonOrderPaymentNotification, send_lesson_order_email, handle_lessons_enrollment),
        "school": (SchoolOrder, SchoolOrderPaymentNotification, send_school_order_email, handle_schools_enrollment),
    }
    if source_prefix not in model_map:
        boipa_logger.error(f"❌ Source prefix '{source_prefix}' not recognized")
        return HttpResponse("Source prefix not recognized", status=400)

    OrderModel, NotificationModel, email_func, enrollment_func = model_map[source_prefix]

    # Normalize useful fields
    tx_id = data.get("txId", "")
    result = data.get("result", "")
    status = data.get("status", "")

    # Quick success gate (BOIPA sends both 'status' and/or 'result')
    is_success = (result.lower() == "success") or (status.upper() == "CAPTURED")

    try:
        order = OrderModel.objects.get(id=order_id)
    except OrderModel.DoesNotExist:
        boipa_logger.error(f"❌ Order {order_id} not found in {OrderModel.__name__}")
        return HttpResponse("Order not found", status=404)

    # Idempotency: if we already have a notification with this txId, return 200
    if tx_id and NotificationModel.objects.filter(order=order, txId=tx_id).exists():
        boipa_logger.info(f"ℹ️ Duplicate notification ignored for order {order.id}, txId={tx_id}")
        return HttpResponse("Already processed", status=200)

    if not is_success:
        boipa_logger.warning(
            f"Payment not marked as paid (result={result}, status={status}) for order {order.id}"
        )
        # Still persist a notification record for audit
        NotificationModel.objects.create(
            order=order,
            txId=tx_id,
            merchantTxId=merchantTxId,
            country=data.get("country", ""),
            amount=data.get("amount"),
            currency=data.get("currency", ""),
            action=data.get("action", ""),
            auth_code=data.get("auth_code", ""),
            acquirer=data.get("acquirer", ""),
            acquirerAmount=data.get("acquirerAmount"),
            merchantId=data.get("merchantId", ""),
            brandId=data.get("brandId", ""),
            customerId=data.get("customerId", ""),
            acquirerCurrency=data.get("acquirerCurrency", ""),
            paymentSolutionId=data.get("paymentSolutionId"),
            status=status or "",
            errorMessage=data.get("errorMessage", "Not successful"),
        )
        return HttpResponse("Payment not successful", status=200)

    # ---- SUCCESS path: mark paid and create notification atomically ----
    def _to_decimal(v):
        if v in (None, ""):
            return None
        try:
            return Decimal(str(v))
        except (InvalidOperation, TypeError):
            return None

    with transaction.atomic():
        # Mark order paid + attach txId
        order.paid = True
        if tx_id:
            order.txId = tx_id
        order.save(update_fields=["paid", "txId"] if tx_id else ["paid"])
        boipa_logger.debug(f"✅ Order saved: id={order.id}, paid={order.paid}, txId={order.txId}")

        # Create notification row
        NotificationModel.objects.create(
            order=order,
            txId=tx_id,
            merchantTxId=merchantTxId,
            country=data.get("country", ""),
            amount=_to_decimal(data.get("amount")),
            currency=data.get("currency", ""),
            action=data.get("action", ""),
            auth_code=data.get("auth_code", "") or data.get("paymentSolutionDetails", ""),
            acquirer=data.get("acquirer", ""),
            acquirerAmount=_to_decimal(data.get("acquirerAmount")),
            merchantId=data.get("merchantId", ""),
            brandId=data.get("brandId", ""),
            customerId=data.get("customerId", ""),
            acquirerCurrency=data.get("acquirerCurrency", ""),
            paymentSolutionId=data.get("paymentSolutionId"),
            status=status or "",
            errorMessage=data.get("errorMessage", "No error message provided"),
        )
        boipa_logger.info(f"📝 Payment notification record created for order {order.id}")

        # Defer risky follow-ups until AFTER commit so they cannot roll back 'paid=True'
        def _post_commit():
            # Enrollment first (if applicable)
            if enrollment_func:
                try:
                    enrollment_func(order)
                    boipa_logger.debug(f"📚 Enrollment done for order {order.id}")
                except IntegrityError:
                    # Unique constraint hit → enrollment already exists
                    boipa_logger.warning(f"⚠️ Enrollment duplicate for order {order.id} – skipping")
                except Exception as e:
                    boipa_logger.error(f"❌ Enrollment failed for order {order.id}: {e}")

            # Then email
            try:
                email_func(order.id)
                boipa_logger.debug(f"📧 Email dispatched for order {order.id}")
            except Exception as e:
                boipa_logger.error(f"❌ Email send failed for order {order.id}: {e}")

        transaction.on_commit(_post_commit)

    return HttpResponse("Payment processed successfully", status=200)

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
