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
from coupons.models import Coupon
from django.urls import reverse


def order_create(request):
    if not request.user.is_authenticated:
        signup_url = reverse('account_signup')
        return redirect(f'{signup_url}?{REDIRECT_FIELD_NAME}={request.get_full_path()}')

    # ✅ Handle coupon code in POST
    if request.method == "POST":
        posted_coupon = request.POST.get('coupon_code', '').strip()
        if posted_coupon:
            request.session['applied_coupon'] = posted_coupon
            print(f">>> DEBUG: Coupon stored in session: {posted_coupon}")

    coupon_code = request.session.get('applied_coupon', '')
    print(f">>> DEBUG: Coupon retrieved from session: {coupon_code}")

    current_user = request.user
    cart = Cart(request)  # Your cart class

    # ✅ Attempt to get first valid product
    product = None
    for product_id, variation_id, quantity in cart:
        try:
            product = PublicSwimProduct.objects.get(id=product_id)
            break
        except PublicSwimProduct.DoesNotExist:
            continue

    if not product:
        return HttpResponse("No valid product in cart")

    # ✅ Calculate total
    total = 0
    for product_id, variation_id, quantity in cart:
        try:
            variation = PriceVariant.objects.get(id=variation_id)
            total += variation.price * quantity
        except PriceVariant.DoesNotExist:
            continue

    print(f">>> DEBUG: Total before discount: €{total:.2f}")

    # ✅ Coupon application (but don't update DB yet)
    discount_amount = 0
    applied_coupon = None

    if coupon_code:
        try:
            coupon = Coupon.objects.get(code__iexact=coupon_code)
            print(">>> DEBUG: Coupon status check")
            print(f"    - code: {coupon.code}")
            print(f"    - active: {coupon.active}")
            print(f"    - valid_from: {coupon.valid_from}")
            print(f"    - valid_to: {coupon.valid_to}")
            print(f"    - balance_remaining: {coupon.balance_remaining}")
            print(f"    - now: {timezone.now()}")
            print(f"    - is_valid result: {coupon.is_valid()}")
            if coupon.is_valid():
                applied_coupon = coupon
                if coupon.discount_type == 'fixed':
                    discount_amount = min(coupon.discount_value, coupon.balance_remaining, total)
                elif coupon.discount_type == 'percent':
                    discount_amount = total * coupon.discount_value / 100
                    # For percentage coupons, balance_remaining doesn't apply
                print(f">>> DEBUG: Valid coupon applied: {coupon.code}, Discount: €{discount_amount:.2f}")
            else:
                print(f">>> DEBUG: Coupon invalid or expired: {coupon_code}")
        except Coupon.DoesNotExist:
            print(f">>> DEBUG: Coupon not found: {coupon_code}")
    else:
        print(">>> DEBUG: No coupon code provided")

    total -= discount_amount
    print(f">>> DEBUG: Final total after discount: €{total:.2f}")

    # ✅ Create the order (status: pending if you're tracking that)
    next_occurrence = get_next_occurrence(product.day_of_week)
    order = Order.objects.create(
        user=request.user,
        booking=next_occurrence,
        product=product,
        coupon=applied_coupon,
        discount_amount=discount_amount
    )

    for product_id, variation_id, quantity in cart:
        try:
            product = PublicSwimProduct.objects.get(id=product_id)
            variation = PriceVariant.objects.get(id=variation_id)
            OrderItem.objects.create(order=order, variant=variation, quantity=quantity)
        except (PublicSwimProduct.DoesNotExist, PriceVariant.DoesNotExist) as e:
            return HttpResponse(f"Error processing order: {e}")

    cart.clear()
    request.session['order_id'] = order.id
    order_created(order.id)

    # ⚠️ DO NOT update coupon balance or mark order as paid here!
    return redirect(reverse('swims_payment:process'))  # you can fix this target later



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
        'current_user': request.user,
        'discount': order.discount_amount,
        'coupon': order.coupon,
    })


def order_created(order_id):
    # Just for logging, hooks, or legacy calls
    order = Order.objects.get(id=order_id)
    return f"Order {order_id} created successfully!"