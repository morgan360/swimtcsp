from django.contrib import messages
from django.conf import settings
from django.shortcuts import render, redirect, reverse, \
    get_object_or_404
from django.views.decorators.http import require_POST
from lessons.models import Product
from schools.models import ScoLessons, ScoSchool
from users.models import Swimling
from .cart import Cart
from .forms import CartAddProductForm, NewSwimlingForm, DirectOrderForm
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.http import Http404
from django.urls import reverse
from lessons_orders.models import Order as LessonOrder, OrderItem as LessonOrderItem
from schools_orders.models import Order as SchoolOrder, OrderItem as SchoolOrderItem
from lessons_bookings.models import Term
from utils.terms_utils import get_term_context_data
from schools_bookings.models import ScoTerm
from utils.terms_utils import get_current_term, get_current_sco_term, get_next_term
from boipa.views import initiate_boipa_payment_session
from lessons_bookings.utils.enrollment import handle_lessons_enrollment
from django.http import HttpResponse
from coupons.forms import CouponApplyForm
from coupons.models import Coupon
from coupons.services import CouponService
from django.core.exceptions import ValidationError
import logging


def _ensure_rebooking_open(request):
    """Redirect to the dashboard with an error if rebooking is closed."""
    term_data = get_term_context_data()
    current_phase = term_data.get('current_phase_id')

    if current_phase != 'RB':
        messages.error(request, "Rebooking is not currently available.")
        return redirect('swimling_dashboard:guardian_dashboard')

    return None


# Create a logger object
logger = logging.getLogger('cart')


@login_required
@require_POST
def cart_add(request, product_id, type):  # type could be 'lesson' or 'school'
    cart = Cart(request)
    if type == 'lesson':
        product = get_object_or_404(Product, id=product_id)
    elif type == 'school':
        product = get_object_or_404(ScoLessons, id=product_id)
    else:
        raise Http404("Product type is not defined")

    form = CartAddProductForm(user=request.user, data=request.POST)
    if form.is_valid():
        swimling = form.cleaned_data['swimling']
        swimling_id = swimling.id

        # Call the add method with the correct parameters including type
        cart.add(product=product, type=type, swimling_id=swimling_id)

        messages.success(request, "Item successfully added to cart.")
        return redirect('shopping_cart:cart_detail')
    else:
        messages.error(request, "There was an error with your form submission.")
        return redirect('some_error_handling_view')


@login_required
@require_POST
def cart_remove(request, product_id, type, swimling_id):
    cart = Cart(request)
    cart_key = f"{type}_{product_id}_{swimling_id}"
    try:
        cart.remove(cart_key)
        messages.success(request, "Item removed from cart.")
    except KeyError:
        messages.error(request, "Item not found in cart.")
    return redirect('shopping_cart:cart_detail')


def cart_detail(request):
    cart = Cart(request)
    cart_items = []
    total_price = Decimal('0.00')

    for item_key, item_data in cart.cart.items():
        product_type, product_id, swimling_id = item_key.split('_')

        if product_type == 'lesson':
            product = Product.objects.filter(id=product_id).first()
        elif product_type == 'school':
            product = ScoLessons.objects.filter(id=product_id).first()
        else:
            continue  # skip unknown types

        swimling = Swimling.objects.filter(id=swimling_id).first()
        if not product or not swimling:
            continue

        item_total = Decimal(item_data['price']) * item_data['quantity']
        total_price += item_total

        cart_items.append({
            'product_id': product_id,
            'product': product,
            'price': item_data['price'],
            'swimling': swimling,
            'total_price': item_total,
            'type': product_type,
        })

    # Include the coupon form
    coupon_form = CouponApplyForm()

    return render(request, 'shopping_cart/detail.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'coupon_form': coupon_form,
    })

    # return render(request, 'shopping_cart/detail.html', {'cart_items': cart_items, 'total_price': total_price})


###################### Payment Process ###################


def payment_completed(request):
    return render(request, 'payment/completed.html')


def payment_canceled(request):
    return render(request, 'payment/canceled.html')




@login_required
def payment_process(request):
    if 'cart' not in request.session or not request.session['cart']:
        return HttpResponse("No items in cart.", status=400)

    cart = Cart(request)
    cart_type = request.session.get(f"{settings.CART_SESSION_ID}_type", None)
    total_price = Decimal('0.00')

    # Step 1: Create order based on cart type
    if cart_type == 'lesson':
        order = LessonOrder.objects.create(user=request.user)
        from utils.terms_utils import get_term_context_data

        term_data = get_term_context_data()
        phase = term_data['current_phase_id']
        term = term_data['next_term'] if phase in ['RB', 'BN'] else term_data['current_term']

        # Pass a lambda so the function signature stays the same
        total_price = process_order_items(
            cart,
            LessonOrderItem,
            order,
            Product,
            lambda: term
        )
    elif cart_type == 'school':
        order = SchoolOrder.objects.create(user=request.user)
        total_price = process_order_items(cart, SchoolOrderItem, order, ScoLessons, get_current_sco_term)
    else:
        return HttpResponse("Invalid product type in cart.", status=400)

    # Step 2: Handle coupon if present
    coupon_code = request.POST.get("code", "").strip()
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            service = CouponService(coupon)
            discount = service.apply(purchase_obj=order, amount=total_price, user=request.user)
            total_price -= discount

            # ✅ Persist coupon info to order
            order.coupon = coupon
            order.discount_amount = discount

            print(f"[Coupon] Applied {coupon_code} for €{discount}")
        except Coupon.DoesNotExist:
            print(f"[Coupon] Invalid code: {coupon_code}")
        except ValidationError as e:
            print(f"[Coupon] Error: {str(e)}")

    # Step 3: Save the final amount and clear cart
    order.amount = total_price
    order.save()

    cart.clear()
    request.session['order_id'] = order.id
    order_ref = f"{cart_type}_{order.id}"

    return redirect('boipa:initiate_payment_session', order_ref=order_ref, total_price=str(total_price))


def process_order_items(cart, OrderItemModel, order, ProductModel, get_term_func):
    total_price = Decimal('0.00')  # Initialize total_price
    for item_key, item_data in cart.cart.items():
        product_id = item_data['product_id']
        product = get_object_or_404(ProductModel, id=product_id)
        swimling = get_object_or_404(Swimling, id=item_data['swimling_id'])
        quantity = item_data.get('quantity', 1)
        price = Decimal(item_data['price'])

        OrderItemModel.objects.create(
            order=order,
            product=product,
            price=price,
            quantity=quantity,
            swimling=swimling,
            term=get_term_func(),
        )
        total_price += price * quantity  # Add to total_price correctly

    order.amount = total_price  # Assign the total to the order
    order.save()
    return total_price  # Return the calculated total_price


def order_created(order_id):
    # Retrieve the order object based on the provided order_id
    order = Order.objects.get(id=order_id)
    # Not used yet might be necessary for emails etc..
    # Return a success message or any relevant data
    return f"Order {order_id} created successfully!"


def direct_order(request, swimling_id, school_id, active_term):
    """Takes a booking from the Swimling panel for a particular swimling in a particular school and allows
    the user to choose a course from that school."""
    swimling = get_object_or_404(Swimling, id=swimling_id)
    school = get_object_or_404(ScoSchool, id=school_id)
    term_instance = get_object_or_404(ScoTerm, pk=active_term)
    if request.method == 'POST':
        form = DirectOrderForm(request.POST, school_id=school_id)
        if form.is_valid():
            # Extract the selected course from the form
            selected_course = form.cleaned_data['lesson']
            total_price = selected_course.price  # Assuming the 'ScoLessons' model has a 'price' field
            term = term_instance
            # Create the main order
            order = SchoolOrder.objects.create(
                user=request.user,
                school=school,
                amount=total_price
            )

            # Create an order item associated with the order
            order_item = SchoolOrderItem.objects.create(
                order=order,
                swimling=swimling,
                product=selected_course,
                price=total_price,
                quantity=1,  # Assuming a quantity of 1 for simplicity
                term=term
            )

            order_ref = f"school_{order.id}"

            # Redirect to initiate payment session with the total price and order reference
            return redirect('boipa:initiate_payment_session', order_ref=order_ref, total_price=str(total_price))
    else:
        form = DirectOrderForm(school_id=school_id)

    return render(request, 'direct_order.html', {
        'form': form,
        'swimling': swimling,
        'school': school,
        'school_id': school_id
    })


@login_required
def review_rebooking(request, swimling_id, product_id):
    phase_guard = _ensure_rebooking_open(request)
    if phase_guard:
        return phase_guard

    """Displays the order details for review before confirming."""
    swimling = get_object_or_404(Swimling, id=swimling_id)
    lesson = get_object_or_404(Product, id=product_id)

    if swimling.guardian != request.user and not request.user.is_staff:
        messages.error(request, "You do not have permission to rebook for this swimling.")
        return redirect('swimling_dashboard:guardian_dashboard')

    if request.method == 'POST':
        # Redirect to the confirmation view
        return redirect('shopping_cart:confirm_rebooking', swimling_id=swimling_id, product_id=product_id)

    return render(request, 'shopping_cart/direct_rebooking.html', {
        'swimling': swimling,
        'lesson': lesson,
    })


@login_required
def direct_rebooking(request, swimling_id, product_id):
    phase_guard = _ensure_rebooking_open(request)
    if phase_guard:
        return phase_guard

    """Handles the final order submission and initiates the payment process."""
    swimling = get_object_or_404(Swimling, id=swimling_id)
    lesson = get_object_or_404(Product, id=product_id)

    if swimling.guardian != request.user and not request.user.is_staff:
        messages.error(request, "You do not have permission to rebook for this swimling.")
        return redirect('swimling_dashboard:guardian_dashboard')

    if request.method == 'POST':
        total_price = lesson.price
        next_term = get_next_term()
        print('term', next_term)

        # Create the main order
        order = LessonOrder.objects.create(
            user=request.user,
            amount=total_price
        )

        # Create an order item associated with the order
        order_item = LessonOrderItem.objects.create(
            order=order,
            swimling=swimling,
            product=lesson,
            price=total_price,
            quantity=1,  # Assuming a quantity of 1 for simplicity
            term=next_term
        )

        order_ref = f"lesson_{order.id}"

        # Redirect to initiate payment session with the total price and order reference
        return redirect('boipa:initiate_payment_session', order_ref=order_ref, total_price=str(total_price))

    # Optionally handle GET requests or any other logic
    return redirect('shopping_cart:review_rebooking', swimling_id=swimling_id, product_id=product_id)


# Show order first
def review_waiting_list_booking(request, swimling_id, product_id):
    """Displays the order details for review before confirming for waiting list bookings."""
    swimling = get_object_or_404(Swimling, id=swimling_id)
    lesson = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        # Redirect to the confirmation view
        return redirect('shopping_cart:confirm_waiting_list_booking', swimling_id=swimling_id, product_id=product_id)

    return render(request, 'shopping_cart/review_waiting_list_booking.html', {
        'swimling': swimling,
        'lesson': lesson,
    })


def confirm_waiting_list_booking(request, swimling_id, product_id):
    """Handles the final order submission and initiates the payment process for waiting list bookings."""
    swimling = get_object_or_404(Swimling, id=swimling_id)
    lesson = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        total_price = lesson.price
        current_term = get_current_term()
        print('term', current_term)

        # Create the main order
        order = LessonOrder.objects.create(
            user=request.user,
            amount=total_price
        )

        # Create an order item associated with the order
        order_item = LessonOrderItem.objects.create(
            order=order,
            swimling=swimling,
            product=lesson,
            price=total_price,
            quantity=1,  # Assuming a quantity of 1 for simplicity
            term=current_term  # Use current term for waiting list bookings
        )

        order_ref = f"lesson_{order.id}"

        # Redirect to initiate payment session with the total price and order reference
        return redirect('boipa:initiate_payment_session', order_ref=order_ref, total_price=str(total_price))

    # Optionally handle GET requests or any other logic
    return redirect('shopping_cart:review_waiting_list_booking', swimling_id=swimling_id, product_id=product_id)
