from django.shortcuts import render, redirect, get_object_or_404
from .models import PublicSwimCategory, PublicSwimProduct, PriceVariant
from swims_orders.models import Order, OrderItem
from django.utils import timezone
from datetime import timedelta
from utils.date_utils import get_next_occurrence
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import time
from .forms import ParticipantQuantityForm
# Assume a function to create BOIPA payment session, replace with your actual function
from boipa.views import initiate_boipa_payment_session
from coupons.models import Coupon
from django.utils.timezone import now as tz_now
from swims_orders.tasks import send_order_email


def product_list(request, category_slug=None):
    category = None
    categories = PublicSwimCategory.objects.all()
    products = PublicSwimProduct.objects.filter(available=True)
    if category_slug:
        category = get_object_or_404(PublicSwimCategory, slug=category_slug)
        products = products.filter(category=category)

    # Get the prices
    price_variants = PriceVariant.objects.all()

    # Calculate the next occurrence date for each product
    today = timezone.now().date()
    for product in products:
        next_occurrence = get_next_occurrence(product.day_of_week)
        product.next_occurrence_date = next_occurrence

    context = {'category': category,
               'categories': categories,
               'products': products,
               'price_variants': price_variants,
               }

    return render(request,
                  'swims/product/list.html',
                  context)



@login_required
@login_required
def product_detail(request, id, slug):
    product = get_object_or_404(PublicSwimProduct, id=id, slug=slug, available=True)
    price_variants = PriceVariant.objects.filter(product=product)
    quantities = range(0, 6)

    if request.method == 'POST':
        # Store coupon
        posted_coupon = request.POST.get('coupon_code', '').strip()
        if posted_coupon:
            request.session['applied_coupon'] = posted_coupon
            print(f">>> DEBUG: Coupon stored in session from product_detail: {posted_coupon}")

        total_amount = 0
        order_items = []

        # Calculate order total
        for variant in price_variants:
            quantity = int(request.POST.get(f'quantity_{variant.id}', 0))
            if quantity > 0:
                total_amount += quantity * variant.price
                order_items.append((variant, quantity))

        # Apply coupon
        applied_coupon = None
        discount_amount = 0
        coupon_code = request.session.get('applied_coupon', '')
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code__iexact=coupon_code)
                if coupon.is_valid():
                    applied_coupon = coupon
                    if coupon.discount_type == 'fixed':
                        discount_amount = min(coupon.discount_value, coupon.balance_remaining, total_amount)
                    elif coupon.discount_type == 'percent':
                        discount_amount = min(total_amount * coupon.discount_value / 100, coupon.balance_remaining)

                    coupon.balance_remaining -= discount_amount
                    coupon.save()
                    total_amount -= discount_amount
                else:
                    print(f">>> DEBUG: Coupon {coupon_code} is not valid.")
            except Coupon.DoesNotExist:
                print(f">>> DEBUG: Coupon {coupon_code} not found.")

        if order_items:
            next_occurrence_date = get_next_occurrence(product.day_of_week)
            order = Order.objects.create(
                user=request.user,
                product=product,
                booking=next_occurrence_date,
                paid=False,
                amount=total_amount,
                coupon=applied_coupon,       # ✅ included
                discount_amount=discount_amount,  # ✅ included
            )
            for variant, quantity in order_items:
                OrderItem.objects.create(order=order, variant=variant, quantity=quantity)

            if total_amount > 0:
                order_ref = f"swims_{order.id}_{int(time.time())}"
                return redirect(reverse('boipa:initiate_payment_session', kwargs={
                    'order_ref': order_ref,
                    'total_price': str(total_amount)
                }))
            else:
                # Fully paid by coupon
                order.paid = True
                order.save()
                order.refresh_from_db()

                if order.paid:
                    send_order_email(order.id)  # ✅ pulls discount info from order record
                return render(request, 'swims_orders/order/created.html', {
                    'order': order,
                    'order_items': order.items.all(),
                    'current_user': request.user,
                    'discount': discount_amount,         # ✅ for template display
                    'coupon': applied_coupon,            # ✅ for template display
                })
        else:
            print(">>> DEBUG: No items selected, not proceeding.")

    next_occurrence_date = get_next_occurrence(product.day_of_week)
    return render(request, 'swims/product/detail.html', {
        'product': product,
        'price_variants': price_variants,
        'quantities': quantities,
        'next_occurrence_date': next_occurrence_date,
    })


def calculate_total(request):
    print(request.POST)  # Debugging: check what's being posted
    total = 0
    for key, value in request.POST.items():
        if key.startswith('quantity_'):
            variant_id = key.split('_')[1]
            quantity = int(value)
            try:
                variant = PriceVariant.objects.get(id=variant_id)
                total += variant.price * quantity
            except PriceVariant.DoesNotExist:
                continue
    return render(request, 'swims/partials/total_price.html', {'total': total})


@login_required
def validate_coupon(request):
    """HTMX endpoint to validate coupon for swims and return discount preview"""
    from django.views.decorators.http import require_POST
    from coupons.services import CouponService
    from django.core.exceptions import ValidationError
    from decimal import Decimal

    if request.method != 'POST':
        return HttpResponse("Method not allowed", status=405)

    coupon_code = request.POST.get("code", "").strip()

    # Calculate cart total from form quantities
    total_price = Decimal('0.00')
    for key, value in request.POST.items():
        if key.startswith('quantity_'):
            variant_id = key.split('_')[1]
            quantity = int(value) if value else 0
            try:
                variant = PriceVariant.objects.get(id=variant_id)
                total_price += variant.price * quantity
            except PriceVariant.DoesNotExist:
                continue

    # Default values
    discount_amount = Decimal('0.00')
    error_message = None
    success = False

    if not coupon_code:
        error_message = "Please enter a coupon code"
    elif total_price == 0:
        error_message = "Please select at least one ticket before applying a coupon"
    else:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            service = CouponService(coupon)

            # Validate without applying (dry run) - specify swims context
            service.validate(user=request.user, amount=total_price, context='swims')

            # Calculate discount
            if coupon.discount_type == 'fixed':
                discount_amount = min(total_price, coupon.balance_remaining)
            elif coupon.discount_type == 'percent':
                discount_amount = total_price * (coupon.discount_value / 100)
                discount_amount = min(discount_amount, coupon.balance_remaining)

            # Store in session for later use
            request.session['applied_coupon'] = coupon_code
            request.session['swim_coupon_discount'] = str(discount_amount)
            success = True

        except Coupon.DoesNotExist:
            error_message = "Invalid coupon code"
        except ValidationError as e:
            error_message = str(e)

    final_price = max(total_price - discount_amount, Decimal('0.00'))

    # Return HTML fragment for HTMX
    return render(request, 'swims/partials/_coupon_result.html', {
        'success': success,
        'error_message': error_message,
        'coupon_code': coupon_code if success else None,
        'discount_amount': discount_amount,
        'total_price': total_price,
        'final_price': final_price,
    })


@login_required
def remove_coupon(request):
    """Remove coupon from session"""
    if request.method == 'POST':
        if 'applied_coupon' in request.session:
            del request.session['applied_coupon']
        if 'swim_coupon_discount' in request.session:
            del request.session['swim_coupon_discount']

    return redirect(request.META.get('HTTP_REFERER', 'swims:product_list'))