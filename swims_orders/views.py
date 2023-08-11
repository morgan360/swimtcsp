from django.urls import reverse
from django.shortcuts import render, redirect
from .models import Order, OrderItem
from swims.models import PublicSwimProduct, PriceVariant
from swims_cart.cart import Cart
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from utils.date_utils import get_next_occurrence

@login_required
def order_create(request):
    order_type = request.GET['value']
    current_user = request.user
    cart = Cart(request)  # Assuming you've imported the Cart class properly

    # Retrieve the first product_id from the cart before creating the order
    product_id = None
    for product_id, _, _ in cart:  # Iterate through the cart items to get the first product_id
        break
    try:
        product = PublicSwimProduct.objects.get(id=product_id)
    except Product.DoesNotExist:
        # Handle the case where the product_id does not exist
        # For example, raise an exception or return an error response
        return HttpResponse("Product does not exist")

    # Now you can access the day_of_week from the product instance
    # day_of_week = product.day_of_week

    next_occurrence = get_next_occurrence(product.day_of_week)
    order = Order.objects.create(user=request.user, booking=next_occurrence, product_id=product_id)

    for product_id, variation_id, quantity in cart:
        product = PublicSwimProduct.objects.get(id=product_id)
        variations = PriceVariant.objects.get(id=variation_id)
        # Create each item
        OrderItem.objects.create(order=order, product=product,
                                 variant=variations.variant,
                                 price=variations.price,
                                 quantity=quantity)

    cart.clear()
    order_created(order.id)
    # Set the order in the session
    request.session['order_id'] = order.id
    # redirect for payment
    return redirect(reverse('swims_payment:process'))

    current_user = request.user
    # Retrieve the order items for the created order
    order_items = OrderItem.objects.filter(order=order)
    return render(request,
                  'swims_orders/order/created.html',
                  {'order': order,
                   'order_type': order_type,
                   'order_items': order_items,
                   # Pass the order_items to the template
                   'current_user': current_user})


def order_created(order_id):
    # Retrieve the order object based on the provided order_id
    order = Order.objects.get(id=order_id)

    # Perform any additional actions or processing for the order creation
    # For example, you can send email notifications, update inventory, etc.

    # Return a success message or any relevant data
    return f"Order {order_id} created successfully!"
