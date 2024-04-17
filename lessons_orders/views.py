from django.urls import reverse
from django.shortcuts import render, redirect, reverse, \
    get_object_or_404
from .models import Order, OrderItem
from lessons.models import Product
from users.models import Swimling
from lessons_cart.cart import Cart
from django.contrib.auth.decorators import login_required
from lessons_bookings.models import Term
from utils.terms_utils import get_current_term
from decimal import Decimal
from django.conf import settings
from boipa.views import initiate_boipa_payment_session
from lessons_bookings.utils.enrollment import handle_lessons_enrollment

def payment_completed(request):
    return render(request, 'payment/completed.html')


def payment_canceled(request):
    return render(request, 'payment/canceled.html')



def payment_process(request):
    if 'cart' not in request.session or not request.session['cart']:
        return HttpResponse("No items in cart.", status=400)

    cart = Cart(request)
    if not cart.cart:
        return HttpResponse("No items in cart.", status=400)  # Extra check if cart is indeed empty

    try:
        order = Order.objects.create(user=request.user)
        total_price = Decimal('0.00')

        for item_key, item_data in cart.cart.items():
            product_id, swimling_id = item_key.split('_')
            product = get_object_or_404(Product, id=product_id)
            swimling = get_object_or_404(Swimling, id=swimling_id)
            quantity = item_data.get('quantity', 1)
            price = Decimal(item_data['price'])

            OrderItem.objects.create(
                order=order,
                product=product,
                price=price,
                quantity=quantity,
                swimling=swimling,
                term=get_current_term()
            )
            total_price += price * quantity  # Ensure price is multiplied by quantity

        order.amount = total_price
        order.save()

        cart.clear()  # Clear the cart after all order processing is done
        request.session['order_id'] = order.id

        order_ref = f"lessons_{order.id}"
        return redirect(reverse('boipa:initiate_payment_session', kwargs={'order_ref': order_ref, 'total_price': str(total_price)}))
    except Exception as e:
        # Handle possible exceptions that could occur during order processing
        return HttpResponse(f"An error occurred: {str(e)}", status=500)


def order_created(order_id):
    # Retrieve the order object based on the provided order_id
    order = Order.objects.get(id=order_id)
    # Not used yet might be necessary for emails etc..
    # Return a success message or any relevant data
    return f"Order {order_id} created successfully!"
