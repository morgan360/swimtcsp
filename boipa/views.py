from django.shortcuts import render, redirect
import requests
import os
import logging
from urllib.parse import urlencode
from dotenv import load_dotenv
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.conf import settings
import os
import logging
import time
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import SwimOrderPaymentNotification, LessonOrderPaymentNotification, SchoolOrderPaymentNotification
from swims_orders.models import Order as SwimOrder
from lessons_orders.models import Order as LessonOrder
from schools_orders.models import Order as SchoolOrder
from django.http import QueryDict
from django.urls import reverse
from lessons_bookings.utils.enrollment import handle_lessons_enrollment
from django.db import transaction
from .payment_functions import get_boipa_session_token  # If external functions are used
from django.conf import settings

# Initialize logging
payments_logger = logging.getLogger('payments')


@require_POST  # Ensures this view only handles POST requests
def initiate_boipa_payment_session(request, order_ref, total_price):
    """
    Initiates a payment session for BOIPA with the given order reference and total price.
    Redirects to the BOIPA Hosted Payment Page (HPP) if successful, otherwise shows an error page.

    Args:
    request: HttpRequest object.
    order_ref: String, a unique identifier for the order.
    total_price: Decimal, the total price of the transaction.
    """
    token = get_boipa_session_token(order_ref, total_price)
    if token is None:
        logger.error(f"Failed to obtain session token for order_ref {order_ref}")
        return render(request, 'error.html', {'error': 'Unable to obtain session token.'})

    # Construct the HPP URL with the obtained token and include integrationMode
    hpp_url = f"{settings.HPP_FORM}?token={token}&merchantId={settings.BOIPA_MERCHANT_ID}&integrationMode=Standalone"

    # Redirect user to the HPP URL
    return redirect(hpp_url)


# Also in views.py

def payment_response(request):
    """
    Handles the payment response from BOIPA.
    """
    payments_logger.debug(f"Received payment response: {request.GET.dict()}")
    result = request.GET.get('result')
    merchantTxId = request.GET.get('merchantTxId')

    if result == "success":
        # Payment was successful
        return render(request, 'payment_success.html', {'order_ref': merchantTxId, 'message': result})

    elif result == "failure":
        # Payment failed
        return render(request, 'payment_failure.html', {'order_ref ': merchantTxId, 'message': result})
    else:
        # Unrecognized result
        return render(request, 'error.html', {'error_message': 'Unknown payment response.'})


###### Notifications #######

@csrf_exempt  # Disable CSRF protection for this endpoint
def payment_notification(request):
    if request.method == 'POST':
        payments_logger.debug(f"Received payment notification: {request.POST.dict()}")
        data = QueryDict(request.body)
        # Extracting the necessary information
        merchantTxId = data.get('merchantTxId')
        source_prefix, order_id_str = merchantTxId.split("_", 1)
        order_id = int(order_id_str)

        if source_prefix == 'swims':
            with transaction.atomic():
                order = SwimOrder.objects.get(id=order_id)
                order.paid = True
                order.save()
            # Parse the URL-encoded form data
            data = QueryDict(request.body)
            with transaction.atomic():
                # Create a payment notification record
                SwimOrderPaymentNotification.objects.create(
                    order=order,
                    txId=data.get('txId'),
                    merchantTxId=data.get('merchantTxId'),
                    country=data.get('country'),
                    amount=data.get('amount'),
                    currency=data.get('currency'),
                    action=data.get('action'),
                    # Assuming auth_code and other details are extracted correctly from paymentSolutionDetails or similar
                    # auth_code=data.get('auth_code'),
                    acquirer=data.get('acquirer'),
                    acquirerAmount=data.get('acquirerAmount'),
                    merchantId=data.get('merchantId'),
                    brandId=data.get('brandId'),
                    customerId=data.get('customerId'),
                    acquirerCurrency=data.get('acquirerCurrency'),
                    paymentSolutionId=data.get('paymentSolutionId'),
                    status=data.get('status'),
                )

                # Return a successful HTTP response
                return HttpResponse('Payment processed successfully', status=200)

        elif source_prefix == 'lessons':
            # Parse the URL-encoded form data
            data = QueryDict(request.body)
            merchantTxId = data.get('merchantTxId')
            source_prefix, order_id_str = merchantTxId.split("_", 1)
            order_id = int(order_id_str)

            # Create a payment notification record
            with transaction.atomic():
                order = LessonOrder.objects.get(id=order_id)
                order.paid = True
                order.save()

            with transaction.atomic():
                LessonOrderPaymentNotification.objects.create(
                    order=order,
                    txId=data.get('txId'),
                    merchantTxId=data.get('merchantTxId'),
                    country=data.get('country'),
                    amount=data.get('amount'),
                    currency=data.get('currency'),
                    action=data.get('action'),
                    # Assuming auth_code and other details are extracted correctly from paymentSolutionDetails or similar
                    # auth_code=data.get('auth_code'),
                    acquirer=data.get('acquirer'),
                    acquirerAmount=data.get('acquirerAmount'),
                    merchantId=data.get('merchantId'),
                    brandId=data.get('brandId'),
                    customerId=data.get('customerId'),
                    acquirerCurrency=data.get('acquirerCurrency'),
                    paymentSolutionId=data.get('paymentSolutionId'),
                    status=data.get('status'),
                )
                return HttpResponse('Payment processed successfully', status=200)

        elif source_prefix == 'schools':
            data = QueryDict(request.body)
            order_obj = SchoolOrder.objects.get(id=order_id)
            # Create a payment notification record
            SchoolOrderPaymentNotification.objects.create(
                order=order_obj,
                txId=data.get('txId'),
                merchantTxId=data.get('merchantTxId'),
                country=data.get('country'),
                amount=data.get('amount'),
                currency=data.get('currency'),
                action=data.get('action'),
                # Assuming auth_code and other details are extracted correctly from paymentSolutionDetails or similar
                # auth_code=data.get('auth_code'),
                acquirer=data.get('acquirer'),
                acquirerAmount=data.get('acquirerAmount'),
                merchantId=data.get('merchantId'),
                brandId=data.get('brandId'),
                customerId=data.get('customerId'),
                acquirerCurrency=data.get('acquirerCurrency'),
                paymentSolutionId=data.get('paymentSolutionId'),
                status=data.get('status'), )

            return HttpResponse("Notification processed successfully", status=200)

    else:
        # If not a POST request, indicate it's an invalid request method
        return HttpResponse("Invalid request method", status=405)
