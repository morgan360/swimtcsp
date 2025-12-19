from decimal import Decimal
import logging
import requests
from functools import wraps
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
from .payment_functions import create_hpp_payment_link  # NEW BOIPA API function
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


def no_session_save(view_func):
    """
    Decorator to prevent session middleware from trying to save session.
    Used for external payment gateway callbacks where session doesn't exist.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Mark session as accessed but never modified
        # This prevents SessionMiddleware from trying to save it
        if hasattr(request, 'session'):
            request.session.accessed = True
            request.session.modified = False
        response = view_func(request, *args, **kwargs)
        # Prevent session save on response
        if hasattr(response, '_dont_enforce_csrf_checks'):
            response._dont_save_session = True
        return response
    return wrapper


def initiate_boipa_payment_session(request, order_ref, total_price):
    """
    NEW BOIPA API: Create HPP link and redirect user to payment page.

    The new API uses OAuth2 access tokens and creates a complete HPP link
    via API call (no more manual token generation).
    """
    total_price = Decimal(total_price)

    # Optional: Extract payer information from request (user, session, etc.)
    payer_info = None
    if request.user.is_authenticated:
        payer_info = {
            'name': f"{request.user.first_name} {request.user.last_name}".strip() or request.user.email,
            'email': request.user.email,
        }

    # Create HPP link via new BOIPA API
    link_data = create_hpp_payment_link(request, order_ref, total_price, payer_info)

    if link_data is None or 'url' not in link_data:
        boipa_logger.error(f"Failed to create HPP link for order_ref {order_ref}")
        return render(request, 'boipa/error.html', {
            'error': 'Unable to create payment link. Please try again or contact support.'
        })

    hpp_url = link_data['url']
    boipa_logger.info(f"Redirecting to HPP: {hpp_url}")

    # Redirect user to BOIPA Hosted Payment Page
    return redirect(hpp_url)


@csrf_exempt
def payment_response(request):
    boipa_logger = logging.getLogger("boipa")
    import json

    # Disable session modification to avoid SessionInterrupted errors from BOIPA
    try:
        request.session.modified = False
    except AttributeError:
        pass  # Session might not exist when called from external gateway

    boipa_logger.debug(f"Payment response - Method: {request.method}")

    # NEW BOIPA API sends JSON in the body
    data = {}
    if request.method == "POST":
        try:
            raw_body = request.body.decode('utf-8')
            if raw_body:
                data = json.loads(raw_body)
                boipa_logger.debug(f"Payment response - Parsed JSON: {data}")
        except json.JSONDecodeError as e:
            boipa_logger.error(f"Failed to parse JSON body: {e}")
            # Fallback to form-encoded POST data
            data = request.POST.dict()
    else:
        # GET request - use query params
        data = request.GET.dict()

    # Extract relevant fields from new API format
    # New API sends: {"id": "TRN_xxx", "status": "CAPTURED", "reference": "lesson_342", ...}
    status = data.get("status", "")
    reference = data.get("reference", "")  # This is our order reference (e.g., "lesson_342")
    txId = data.get("id", "")  # Transaction ID from BOIPA

    boipa_logger.debug(f"Extracted - status: {status}, reference: {reference}, txId: {txId}")

    # Use reference as merchantTxId for compatibility
    merchantTxId = reference
    result = "success" if status == "CAPTURED" else "failure"

    order_ref = None
    if merchantTxId:
        parts = merchantTxId.split("_")
        if len(parts) >= 2:
            try:
                order_ref = int(parts[1])  # ✅ only second part is numeric ID
            except ValueError:
                order_ref = merchantTxId  # fallback to raw if parsing fails

    # Process payment if successful (NEW BOIPA API sends full data to return_url)
    if result == "success" and order_ref and txId:
        try:
            # Determine order type from merchantTxId prefix
            order = None
            order_type = None

            if merchantTxId.startswith("swims_"):
                from swims_orders.models import Order as SwimOrder
                order = SwimOrder.objects.get(id=order_ref)
                order_type = "swim"
                boipa_logger.info(f"Found SwimOrder {order_ref}")
            elif merchantTxId.startswith("school_"):
                from schools_orders.models import Order as SchoolOrder
                order = SchoolOrder.objects.get(id=order_ref)
                order_type = "school"
                boipa_logger.info(f"Found SchoolOrder {order_ref}")
            else:
                # Default to lesson order (backwards compatibility)
                from lessons_orders.models import Order
                order = Order.objects.get(id=order_ref)
                order_type = "lesson"
                boipa_logger.info(f"Found LessonOrder {order_ref}")

            # Mark order as paid if not already
            if not order.paid:
                order.paid = True
                order.txId = txId
                order.save(update_fields=["paid", "txId"])
                boipa_logger.info(f"✅ Order {order_ref} ({order_type}) marked paid via payment_response")

                # Create enrollments and send emails based on order type
                if order_type == "lesson":
                    try:
                        handle_lessons_enrollment(order)
                        boipa_logger.info(f"📚 Enrollments created for lesson order {order_ref}")
                    except Exception as e:
                        boipa_logger.error(f"❌ Enrollment failed: {e}")

                    try:
                        send_lesson_order_email(order.id)
                        boipa_logger.info(f"📧 Email sent for lesson order {order_ref}")
                    except Exception as e:
                        boipa_logger.error(f"❌ Email failed: {e}")

                elif order_type == "swim":
                    try:
                        from swims_orders.emails import send_swim_order_email
                        send_swim_order_email(order.id)
                        boipa_logger.info(f"📧 Email sent for swim order {order_ref}")
                    except Exception as e:
                        boipa_logger.error(f"❌ Email failed: {e}")

                elif order_type == "school":
                    try:
                        from schools_orders.emails import send_school_order_email
                        send_school_order_email(order.id)
                        boipa_logger.info(f"📧 Email sent for school order {order_ref}")
                    except Exception as e:
                        boipa_logger.error(f"❌ Email failed: {e}")
        except Exception as e:
            boipa_logger.error(f"❌ Error processing payment in payment_response: {e}")

    # Return a simple redirect page since BOIPA will display this on their domain
    # The actual success page will be shown after redirect
    from django.http import HttpResponse

    if result == "success":
        # Build the redirect URL
        redirect_url = request.build_absolute_uri(reverse('home'))

        # Return simple HTML with auto-redirect
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="2;url={redirect_url}">
    <title>Payment Successful</title>
    <style>
        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f9ff; }}
        .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; margin: 0 auto; }}
        h1 {{ color: #16a34a; }}
        .spinner {{ border: 4px solid #f3f3f3; border-top: 4px solid #16a34a; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Payment Successful!</h1>
        <p>Your payment has been processed successfully.</p>
        <p><strong>Order ID:</strong> {order_ref}</p>
        <div class="spinner"></div>
        <p>Redirecting you back to the site...</p>
        <p><a href="{redirect_url}">Click here if not redirected automatically</a></p>
    </div>
</body>
</html>
"""
        return HttpResponse(html)
    elif result == "failure":
        redirect_url = request.build_absolute_uri(reverse('home'))
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="5;url={redirect_url}">
    <title>Payment Failed</title>
    <style>
        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #fef2f2; }}
        .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; margin: 0 auto; }}
        h1 {{ color: #dc2626; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>❌ Payment Failed</h1>
        <p>Your payment could not be processed.</p>
        <p>Redirecting you back to try again...</p>
        <p><a href="{redirect_url}">Click here to return</a></p>
    </div>
</body>
</html>
"""
        return HttpResponse(html)

    # Unknown response
    return HttpResponse("<h1>Unknown payment response</h1>", status=400)




@csrf_exempt
def payment_notification(request):
    import json

    boipa_logger.debug("📥 payment_notification view triggered")
    boipa_logger.debug(f"🔎 Method: {request.method}")
    boipa_logger.debug(f"🔎 Content-Type: {request.headers.get('Content-Type', 'N/A')}")

    # --- Parse incoming data ---
    data = {}
    if request.method == "POST":
        try:
            raw_body = request.body.decode("utf-8")
            boipa_logger.debug(f"🔎 RAW BODY: {raw_body[:500]}...")  # First 500 chars

            # Try JSON first (new BOIPA API)
            if raw_body:
                try:
                    data = json.loads(raw_body)
                    boipa_logger.debug(f"✅ Parsed as JSON")
                except json.JSONDecodeError:
                    # Fallback to form-encoded
                    boipa_logger.debug(f"⚠️ Not JSON, trying form-encoded")
                    data = request.POST.dict()
                    if not data:
                        # Try URL-encoded in body
                        parsed = parse_qs(raw_body)
                        data = {k: v[0] for k, v in parsed.items()}
        except Exception as e:
            boipa_logger.error(f"❌ Failed to parse body: {e}")
            return HttpResponse("Failed to parse request", status=400)
    elif request.method == "GET":
        data = request.GET.dict()
    else:
        return HttpResponse("Invalid request method", status=405)

    boipa_logger.debug(f"📦 Parsed notification data: {data}")

    # Extract merchantTxId from new API format
    # New API sends: {"reference": "lesson_342", ...} instead of {"merchantTxId": "lesson_342"}
    merchantTxId = data.get("merchantTxId") or data.get("reference")
    if not merchantTxId:
        boipa_logger.error(f"❌ merchantTxId/reference missing from payload")
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

    # Normalize useful fields for new API
    # New API sends "id" instead of "txId", and "status" instead of "result"
    tx_id = data.get("id") or data.get("txId", "")  # Try new format first
    result = data.get("result", "")
    status = data.get("status", "")

    # Quick success gate (BOIPA sends both 'status' and/or 'result')
    is_success = (result.lower() == "success") if result else (status.upper() == "CAPTURED")

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
