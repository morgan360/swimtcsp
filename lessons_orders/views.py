from django.urls import reverse
from django.shortcuts import render, redirect
from .models import Order, OrderItem
from lessons.models import Product
from lessons_cart.cart import Cart
from django.contrib.auth.decorators import login_required
from lessons_bookings.context_processors import current_term
from lessons_bookings.models import Term

@login_required
def order_create(request):
    cart = Cart(request)
    order = Order.objects.create(user=request.user)
    # Call the context processor function to populate the request context
    context = current_term(request)
    # Access the context variables, including current_term
    current_term_obj = context['current_term']
    # Retrieve the current_term_id if it exists
    current_term_id = current_term_obj.term_id if current_term_obj else None
    current_term_instance = None
    if current_term_id is not None:
        try:
            current_term_instance = Term.objects.get(term_id=current_term_id)
        except Term.DoesNotExist:
            pass
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
    # Perform any additional actions or processing for the order creation
    # For example, you can send email notifications, update inventory, etc.
    # Return a success message or any relevant data
    return f"Order {order_id} created successfully!"
