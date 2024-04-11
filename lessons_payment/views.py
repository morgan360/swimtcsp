from decimal import Decimal
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
        # Assuming get_total_cost is a method that calculates the total cost
        total_price = order.get_total_cost()

        # Update the order with the total amount


        order.amount = total_price
        order.save()  # Don't forget to save the order after updating

        # Generate a unique order reference
        order_ref = f"lessons_{order.id}"

        # Redirect the user to the BOIPA payment page
        return redirect(reverse('boipa:initiate_payment_session',
                                kwargs={'order_ref': order_ref, 'total_price': str(total_price)}))
    else:
        # Render your payment form template if not a POST request
        return render(request, 'payment/process.html', {'order': order})


def payment_completed(request):
    return render(request, 'payment/completed.html')


def payment_canceled(request):
    return render(request, 'payment/canceled.html')

# Create your views here.
