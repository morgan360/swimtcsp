from django.urls import reverse
from .models import Order, OrderItem
from schools.models import ScoLessons
from shopping_cart.cart import Cart
from django.contrib.auth.decorators import login_required
from schools_bookings.models import ScoTerm
from utils.terms_utils import get_current_sco_term
from django.shortcuts import render, redirect, reverse, \
    get_object_or_404
from users.models import Swimling
from decimal import Decimal
from django.conf import settings
from boipa.views import initiate_boipa_payment_session
# from lessons_bookings.utils.enrollment import handle_schools_enrollment
import logging

logger = logging.getLogger('application')


@login_required
def payment_process(request):
    if 'cart' not in request.session or not request.session['cart']:
        logger.info("Cart is empty.")
        return HttpResponse("No items in cart.", status=400)

    current_term_instance = get_current_sco_term()
    cart = Cart(request)
    cart.clean()
    order = Order.objects.create(user=request.user)
    total_price = Decimal('0.00')

    for item_key, item_data in cart.cart.items():
        product_id, swimling_id = item_key.split('_')
        logger.debug(f"Processing product_id: {product_id}, swimling_id: {swimling_id}")

        product = get_object_or_404(ScoLessons, id=product_id)
        swimling = get_object_or_404(Swimling, id=swimling_id)

        quantity = item_data.get('quantity', 1)
        price = Decimal(item_data['price'])

        OrderItem.objects.create(
            order=order,
            product=product,
            price=price,
            quantity=quantity,
            swimling=swimling,
            term=current_term_instance
        )
        total_price += price * quantity

    order.amount = total_price
    order.save()
    cart.clear()
    request.session['order_id'] = order.id

    order_ref = f"schools_{order.id}"
    logger.info(f"Order reference: {order_ref}")

    return redirect(reverse('boipa:initiate_payment_session',
                            kwargs={'order_ref': order_ref, 'total_price': str(total_price)}))






# @login_required
# def payment_process(request):
#     if 'cart' not in request.session or not request.session['cart']:
#         return HttpResponse("No items in cart.", status=400)
#
#     current_term_instance = get_current_sco_term()
#     cart = Cart(request)
#
#     order = Order.objects.create(user=request.user)
#     total_price = Decimal('0.00')
#
#     for item_key, item_data in cart.cart.items():
#         product_id, swimling_id = item_key.split('_')
#         product = get_object_or_404(ScoLessons, id=product_id)
#         swimling = get_object_or_404(Swimling, id=swimling_id)
#
#         quantity = item_data.get('quantity', 1)
#         price = Decimal(item_data['price'])
#
#         OrderItem.objects.create(
#             order=order,
#             product=product,
#             price=price,
#             quantity=quantity,
#             swimling=swimling,
#             term=current_term_instance
#         )
#         total_price += price*quantity
#
#     order.amount = total_price
#     order.save()
#     # handle_lessons_enrollment(order)
#     cart.clear()
#     request.session['order_id'] = order.id
#
#     order_ref = f"schools_{order.id}"
#     print(order_ref)
#
#     # Redirect the user to the BOIPA payment page
#     return redirect(reverse('boipa:initiate_payment_session',
#                             kwargs={'order_ref': order_ref, 'total_price': str(total_price)}))

def order_created(order_id):
    # Retrieve the order object based on the provided order_id
    order = Order.objects.get(id=order_id)
    # Not used yet might be necessary for emails etc..
    # Return a success message or any relevant data
    return f"Order {order_id} created successfully!"


def payment_completed(request):
    return render(request, 'payment/completed.html')


def payment_canceled(request):
    return render(request, 'payment/canceled.html')