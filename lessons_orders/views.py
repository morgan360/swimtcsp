from django.urls import reverse
from django.shortcuts import render, redirect, reverse, \
    get_object_or_404
from .models import Order, OrderItem
from lessons.models import Product
from lessons_cart.cart import Cart
from django.contrib.auth.decorators import login_required
from lessons_bookings.models import Term
from utils.terms_utils import get_current_term
from decimal import Decimal
from django.conf import settings
from boipa.views import initiate_boipa_payment_session


def payment_process(request):
    order_id = order_create(request)
    order = get_object_or_404(Order, id=order_id)
    # Update the order with the total amount

    total_price = order.get_total_cost()
    order.amount = total_price
    order.save()  # Don't forget to save the order after updating

    # Generate a unique order reference
    order_ref = f"lessons_{order_id}"
    print(order_ref)

    # Redirect the user to the BOIPA payment page
    return redirect(reverse('boipa:initiate_payment_session',
                            kwargs={'order_ref': order_ref, 'total_price': str(total_price)}))

def payment_completed(request):
    return render(request, 'payment/completed.html')


def payment_canceled(request):
    return render(request, 'payment/canceled.html')

# Create your views here.


def order_create(request):
    current_term_instance = get_current_term()
    cart = Cart(request)
    order = Order.objects.create(user=request.user)
    for item in cart:
        swimling_id = int(item['swimling'])  # Convert the ID to an integer
        OrderItem.objects.create(
            order=order,
            product=item['product'],
            price=item['price'],
            quantity=item['quantity'],
            swimling_id=swimling_id,  # Assign the swimling ID
            term=current_term_instance  # Use the Term instance
        )

    # Clear the cart
    cart.clear()

    # Call the order_created function
    # order_created(order.id) # Turned Off

    # Set the order in the session
    request.session['order_id'] = order.id

    # Redirect for payment
    return order.id


def order_created(order_id):
    # Retrieve the order object based on the provided order_id
    order = Order.objects.get(id=order_id)
    # Not used yet might be necessary for emails etc..
    # Return a success message or any relevant data
    return f"Order {order_id} created successfully!"
