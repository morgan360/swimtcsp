from django.urls import reverse
from django.shortcuts import render, redirect
from .models import Order, OrderItem
from swims.models import PublicSwimProduct, PriceVariant
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from utils.date_utils import get_next_occurrence
from django.http import HttpResponse
from django.contrib.auth import REDIRECT_FIELD_NAME
from swims_orders.tasks import send_order_email

def order_create(request):
    if not request.user.is_authenticated:
        signup_url = reverse('account_signup')
        return redirect(f'{signup_url}?{REDIRECT_FIELD_NAME}={request.get_full_path()}')


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
    order_created(order.id)  # Keep this for side effects or logging
    send_order_email(order.id)  # .delay for celery

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
    # Just for logging, hooks, or legacy calls
    order = Order.objects.get(id=order_id)
    return f"Order {order_id} created successfully!"