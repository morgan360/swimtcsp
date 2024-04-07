from django.urls import reverse
from django.shortcuts import render, redirect
from .models import Order, OrderItem
from lessons.models import Product
from lessons_cart.cart import Cart
from django.contrib.auth.decorators import login_required
from lessons_bookings.models import Term
from utils.terms_utils import get_current_term


@login_required
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
    order_created(order.id)

    # Set the order in the session
    request.session['order_id'] = order.id

    # Redirect for payment
    return redirect(reverse('lessons_payment:process'))


def order_created(order_id):
    # Retrieve the order object based on the provided order_id
    order = Order.objects.get(id=order_id)
    # Not used yet might be necessary for emails etc..
    # Return a success message or any relevant data
    return f"Order {order_id} created successfully!"
