from decimal import Decimal
import stripe
from django.conf import settings
from django.shortcuts import render, redirect, reverse, \
    get_object_or_404
from lessons_orders.models import Order
from django.shortcuts import render, redirect, get_object_or_404
from boipa.views import initiate_boipa_payment_session


def payment_process(request):
    order_id = request.session.get('order_id', None)
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        total_price = order.get_total_cost()  # Assuming get_total_cost is a method that calculates the total cost
        order_ref = order_id  # Generate a unique order reference

        # Redirect the user to the BOIPA payment page
        return initiate_boipa_payment_session(request, order_ref, total_price)
    else:
        # Render your payment form template if not a POST request
        return render(request, 'payment/process.html', {'order': order})


def payment_completed(request):
    return render(request, 'payment/completed.html')


def payment_canceled(request):
    return render(request, 'payment/canceled.html')

# Create your views here.
