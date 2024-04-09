from django.urls import reverse
from django.shortcuts import render, redirect
from .models import Order, OrderItem
from schools.models import ScoLessons
from schools_cart.cart import Cart
from django.contrib.auth.decorators import login_required
from schools_bookings.models import ScoTerm
from utils.terms_utils import get_current_sco_term


@login_required
def order_create(request):
    current_term_instance = get_current_sco_term()
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
    return redirect(reverse('schools_payment:payment_process'))


def order_created(order_id):
    # Retrieve the order object based on the provided order_id
    order = Order.objects.get(id=order_id)
    # Perform any additional actions or processing for the order creation
    # For example, you can send email notifications, update inventory, etc.
    # Return a success message or any relevant data
    return f"Order {order_id} created successfully!"
