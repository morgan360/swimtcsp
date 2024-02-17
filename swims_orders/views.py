from django.urls import reverse
from django.shortcuts import render, redirect
from .models import Order, OrderItem
from swims.models import PublicSwimProduct, PriceVariant
from swims_cart.cart import Cart
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from utils.date_utils import get_next_occurrence
from django.http import HttpResponse

@login_required
def order_create(request):
    order_type = request.GET.get('value', 'default_value')
    current_user = request.user
    cart = Cart(request)  # Assuming Cart class is imported

    # Initialize product variable
    product = None

    # Attempt to retrieve the first product from the cart
    for product_id, variation_id, quantity in cart:
        try:
            product = PublicSwimProduct.objects.get(id=product_id)
            break
        except PublicSwimProduct.DoesNotExist:
            continue

    # Check if a valid product is found
    if not product:
        return HttpResponse("No valid product in cart")

    # Create the order with the first found product
    next_occurrence = get_next_occurrence(product.day_of_week)
    order = Order.objects.create(user=request.user, booking=next_occurrence, product=product)

    # Process each cart item
    for product_id, variation_id, quantity in cart:
        try:
            product = PublicSwimProduct.objects.get(id=product_id)
            variation = PriceVariant.objects.get(id=variation_id)
            OrderItem.objects.create(
                order=order,
                variant=variation,  # Pass the PriceVariant instance
                quantity=quantity
            )
        except (PublicSwimProduct.DoesNotExist, PriceVariant.DoesNotExist) as e:
            # Handle exceptions
            return HttpResponse(f"Error processing order: {e}")

    # Clear cart and set session order ID
    cart.clear()
    order_created(order.id)
    request.session['order_id'] = order.id

    # Redirect to payment process
    return redirect(reverse('swims_payment:process'))


def order_confirmation(request):
    # Assuming the order ID is stored in the session after payment
    order_id = request.session.get('order_id')
    if not order_id:
        # Handle case where there is no order ID in session
        return HttpResponse("No order found")

    # Retrieve the order and its items
    order = Order.objects.get(id=order_id)
    order_items = OrderItem.objects.filter(order=order)

    return render(request, 'swims_orders/order/created.html', {
        'order': order,
        'order_items': order_items,
        'current_user': request.user
    })


def order_created(order_id):
    # Retrieve the order object based on the provided order_id
    order = Order.objects.get(id=order_id)

    # Perform any additional actions or processing for the order creation
    # For example, you can send email notifications, update inventory, etc.

    # Return a success message or any relevant data
    return f"Order {order_id} created successfully!"
