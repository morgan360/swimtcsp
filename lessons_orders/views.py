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


login_required


def order_create(request):
    if 'cart' not in request.session or not request.session['cart']:
        return HttpResponse("No items in cart.", status=400)

    current_term_instance = get_current_term()
    cart = Cart(request)
    order = Order.objects.create(user=request.user)
    total_price = Decimal('0.00')

    for item in cart:
        product_id = item.get('product_id')
        if not product_id:
            continue  # Skip items without a product ID

        product = get_object_or_404(Product, id=product_id)
        price = Decimal(item['price'])
        quantity = int(item['quantity'])
        swimling_id = int(item['swimling'])

        OrderItem.objects.create(
            order=order,
            product=product,
            price=price,
            quantity=quantity,
            swimling_id=swimling_id,
            term=current_term_instance
        )
        total_price += price * quantity

    order.amount = total_price
    order.save()

    cart.clear()
    request.session['order_id'] = order.id

    return order.id

def order_created(order_id):
    # Retrieve the order object based on the provided order_id
    order = Order.objects.get(id=order_id)
    # Not used yet might be necessary for emails etc..
    # Return a success message or any relevant data
    return f"Order {order_id} created successfully!"
