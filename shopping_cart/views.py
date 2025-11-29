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

        # Determine the appropriate term for pricing
        term = None
        if type == 'lesson':
            from utils.terms_utils import get_term_context_data
            from lessons_bookings.models import LessonEnrollment
            term_data = get_term_context_data()
            phase = term_data.get('current_phase_id')
            current_term = term_data.get('current_term')
            next_term = term_data.get('next_term')

            # BK phase: Always book into current term
            if phase == 'BK':
                term = current_term
            # BN phase: Always book into next term
            elif phase == 'BN':
                term = next_term
            # RB phase: Check if swimling is currently enrolled
            elif phase == 'RB':
                # Check if swimling has enrollment in current term
                is_enrolled = LessonEnrollment.objects.filter(
                    swimling_id=swimling_id,
                    term=current_term
                ).exists()
                # If enrolled, book into next term (rebooking), otherwise current term (new booking)
                term = next_term if is_enrolled else current_term
            else:
                # Fallback to current term
                term = current_term

        # Call the add method with the correct parameters including type and term
        cart.add(product=product, type=type, swimling_id=swimling_id, term=term)

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

    # Check if there's a validated coupon in the session
    discount_amount = Decimal('0.00')
    coupon_code = None
    final_price = total_price

    if 'coupon_code' in request.session and 'coupon_discount' in request.session:
        coupon_code = request.session['coupon_code']
        discount_amount = Decimal(str(request.session['coupon_discount']))
        final_price = max(total_price - discount_amount, Decimal('0.00'))

    return render(request, 'shopping_cart/detail.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'coupon_form': coupon_form,
        'coupon_code': coupon_code,
        'discount_amount': discount_amount,
        'final_price': final_price,
    })


@login_required
@require_POST
def validate_coupon(request):
    """HTMX endpoint to validate coupon and return discount preview"""
    cart = Cart(request)
    coupon_code = request.POST.get("code", "").strip()

    # Calculate cart total
    total_price = Decimal('0.00')
    for item_key, item_data in cart.cart.items():
        item_total = Decimal(item_data['price']) * item_data['quantity']
        total_price += item_total

    # Default values
    discount_amount = Decimal('0.00')
    error_message = None
    success = False

    if not coupon_code:
        error_message = "Please enter a coupon code"
    else:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            service = CouponService(coupon)

            # Validate without applying (dry run) - specify lessons context
            service.validate(user=request.user, amount=total_price, context='lessons')

            # Calculate discount
            if coupon.discount_type == 'fixed':
                discount_amount = min(total_price, coupon.balance_remaining)
            elif coupon.discount_type == 'percent':
                discount_amount = total_price * (coupon.discount_value / 100)
                # For percentage coupons, balance_remaining doesn't apply

            # Store in session for later use
            request.session['coupon_code'] = coupon_code
            request.session['coupon_discount'] = str(discount_amount)
            success = True

        except Coupon.DoesNotExist:
            error_message = "Invalid coupon code"
        except ValidationError as e:
            error_message = str(e)

    final_price = max(total_price - discount_amount, Decimal('0.00'))

    # Return HTML fragment for HTMX
    return render(request, 'shopping_cart/_coupon_result.html', {
        'success': success,
        'error_message': error_message,
        'coupon_code': coupon_code if success else None,
        'discount_amount': discount_amount,
        'total_price': total_price,
        'final_price': final_price,
    })


@login_required
@require_POST
def remove_coupon(request):
    """Remove coupon from session"""
    if 'coupon_code' in request.session:
        del request.session['coupon_code']
    if 'coupon_discount' in request.session:
        del request.session['coupon_discount']

    return redirect('shopping_cart:cart_detail')


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
        from lessons_bookings.models import LessonEnrollment

        # The term was already determined when adding to cart, so we use the term stored in cart items
        # This ensures we book into the correct term based on enrollment status checked during cart_add
        try:
            total_price = process_order_items_from_cart(
                cart,
                LessonOrderItem,
                order,
                Product
            )
        except ValueError as exc:
            order.delete()
            messages.error(request, str(exc))
            return redirect('shopping_cart:cart_detail')
    elif cart_type == 'school':
        order = SchoolOrder.objects.create(user=request.user)
        try:
            total_price = process_order_items(cart, SchoolOrderItem, order, ScoLessons, get_current_sco_term)
        except ValueError as exc:
            order.delete()
            messages.error(request, str(exc))
            return redirect('shopping_cart:cart_detail')
    else:
        return HttpResponse("Invalid product type in cart.", status=400)

    # Step 2: Handle coupon if present (from session)
    coupon_code = request.session.get('coupon_code')
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            service = CouponService(coupon)
            discount = service.apply(purchase_obj=order, amount=total_price, user=request.user)
            total_price -= discount

            # ✅ Persist coupon info to order
            order.coupon = coupon
            order.discount_amount = discount

            # Clear coupon from session after applying
            del request.session['coupon_code']
            del request.session['coupon_discount']

            logger.info(f"[Coupon] Applied {coupon_code} for €{discount} to order {order.id}")
        except Coupon.DoesNotExist:
            logger.error(f"[Coupon] Invalid code: {coupon_code}")
        except ValidationError as e:
            logger.error(f"[Coupon] Error: {str(e)}")

    # Step 3: Save the final amount and clear cart
    order.amount = total_price
    order.save()

    cart.clear()
    request.session['order_id'] = order.id
    order_ref = f"{cart_type}_{order.id}"

    # Step 4: Check if payment is needed or if order is fully covered by coupon
    if total_price > 0:
        # Standard flow: redirect to BOIPA payment gateway
        return redirect('boipa:initiate_payment_session', order_ref=order_ref, total_price=str(total_price))
    else:
        # Zero-balance flow: order fully paid by coupon
        order.paid = True
        order.save()

        # Handle enrollment based on order type
        if cart_type == 'lesson':
            from lessons_orders.tasks import send_lesson_order_email
            handle_lessons_enrollment(order)
            send_lesson_order_email(order.id)

            return render(request, 'orders/order/created.html', {
                'order': order,
                'order_items': order.items.all(),
            })
        elif cart_type == 'school':
            from schools_bookings.utils.enrollment import handle_schools_enrollment
            from schools_orders.tasks import send_school_order_email
            handle_schools_enrollment(order)
            send_school_order_email(order.id)

            return render(request, 'orders/order/created.html', {
                'order': order,
                'order_items': order.items.all(),
            })
        else:
            return HttpResponse("Invalid cart type", status=400)


def process_order_items_from_cart(cart, OrderItemModel, order, ProductModel):
    """Process order items using term already stored in cart (determined during cart_add)"""
    total_price = Decimal('0.00')
    for item_key, item_data in cart.cart.items():
        product_id = item_data['product_id']
        product = get_object_or_404(ProductModel, id=product_id)
        swimling = get_object_or_404(Swimling, id=item_data['swimling_id'])
        quantity = item_data.get('quantity', 1)
        price = Decimal(item_data['price'])

        # Get term from cart item data (set during cart_add based on enrollment status)
        term_id = item_data.get('term_id')
        if not term_id:
            raise ValueError("We couldn't determine which term to book for right now. Please try again later.")

        term = get_object_or_404(Term, id=term_id)

        OrderItemModel.objects.create(
            order=order,
            product=product,
            price=price,
            quantity=quantity,
            swimling=swimling,
            term=term,
        )
        total_price += price * quantity

    order.amount = total_price
    order.save()
    return total_price


def process_order_items(cart, OrderItemModel, order, ProductModel, get_term_func):
    total_price = Decimal('0.00')  # Initialize total_price
    for item_key, item_data in cart.cart.items():
        product_id = item_data['product_id']
        product = get_object_or_404(ProductModel, id=product_id)
        swimling = get_object_or_404(Swimling, id=item_data['swimling_id'])
        quantity = item_data.get('quantity', 1)
        price = Decimal(item_data['price'])

        term = get_term_func()
        if term is None:
            raise ValueError("We couldn't determine which term to book for right now. Please try again later.")

        OrderItemModel.objects.create(
            order=order,
            product=product,
            price=price,
            quantity=quantity,
            swimling=swimling,
            term=term,
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

            # Check if payment is needed
            if total_price > 0:
                # Standard flow: redirect to BOIPA payment gateway
                order_ref = f"school_{order.id}"
                return redirect('boipa:initiate_payment_session', order_ref=order_ref, total_price=str(total_price))
            else:
                # Zero-balance flow: order fully paid (free or fully discounted)
                from schools_bookings.utils.enrollment import handle_schools_enrollment
                from schools_orders.tasks import send_school_order_email
                order.paid = True
                order.save()
                handle_schools_enrollment(order)
                send_school_order_email(order.id)

                return render(request, 'orders/order/created.html', {
                    'order': order,
                    'order_items': order.items.all(),
                })
    else:
        form = DirectOrderForm(school_id=school_id)

    return render(request, 'direct_order.html', {
        'form': form,
        'swimling': swimling,
        'school': school,
        'school_id': school_id
    })


@login_required
def rebooking_page(request):
    """Displays all swimlings with their current lessons, allowing multi-select rebooking."""
    phase_guard = _ensure_rebooking_open(request)
    if phase_guard:
        return phase_guard

    from utils.terms_utils import get_term_context_data
    from lessons_bookings.models import LessonEnrollment

    term_data = get_term_context_data()
    current_term = term_data.get('current_term')
    next_term = term_data.get('next_term')

    if not current_term or not next_term:
        messages.error(request, "Rebooking is not available at this time.")
        return redirect('swimling_dashboard:guardian_dashboard')

    # Get all swimlings for the current user
    swimlings = Swimling.objects.filter(guardian=request.user)

    # Build list of rebookable swimlings with their current lessons
    rebookable_items = []
    for swimling in swimlings:
        # Get current enrollments
        enrollments = LessonEnrollment.objects.filter(
            swimling=swimling,
            term=current_term
        ).select_related('lesson')

        for enrollment in enrollments:
            lesson = enrollment.lesson
            # Get prorated price for next term
            price = lesson.get_prorated_price(next_term)
            rebookable_items.append({
                'swimling': swimling,
                'lesson': lesson,
                'price': price,
            })

    if request.method == 'POST':
        # Get selected items from checkboxes
        selected_items = request.POST.getlist('selected_items')

        if not selected_items:
            messages.warning(request, "Please select at least one swimling to rebook.")
            return redirect('shopping_cart:rebooking_page')

        # Add each selected item to cart
        cart = Cart(request)
        added_count = 0

        for item_key in selected_items:
            # item_key format: "swimling_id_lesson_id"
            try:
                swimling_id, lesson_id = item_key.split('_')
                swimling = get_object_or_404(Swimling, id=swimling_id, guardian=request.user)
                lesson = get_object_or_404(Product, id=lesson_id)

                # Add to cart with next term for pricing
                cart.add(product=lesson, type='lesson', swimling_id=swimling.id, term=next_term)
                added_count += 1
            except (ValueError, Swimling.DoesNotExist, Product.DoesNotExist):
                continue

        if added_count > 0:
            messages.success(request, f"Successfully added {added_count} lesson(s) to your cart.")
            return redirect('shopping_cart:cart_detail')
        else:
            messages.error(request, "No valid items were added to the cart.")
            return redirect('shopping_cart:rebooking_page')

    return render(request, 'shopping_cart/rebooking_page.html', {
        'rebookable_items': rebookable_items,
        'next_term': next_term,
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
        next_term = get_next_term()
        print('term', next_term)

        if next_term is None:
            messages.error(request, "We couldn't determine the upcoming term for this rebooking. Please try again later.")
            return redirect('swimling_dashboard:guardian_dashboard')

        # Use prorated price if term has started, otherwise full price
        total_price = lesson.get_prorated_price(next_term)

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

        # Check if payment is needed
        if total_price > 0:
            # Standard flow: redirect to BOIPA payment gateway
            order_ref = f"lesson_{order.id}"
            return redirect('boipa:initiate_payment_session', order_ref=order_ref, total_price=str(total_price))
        else:
            # Zero-balance flow: order fully paid (free or fully discounted)
            from lessons_orders.tasks import send_lesson_order_email
            order.paid = True
            order.save()
            handle_lessons_enrollment(order)
            send_lesson_order_email(order.id)

            return render(request, 'orders/order/created.html', {
                'order': order,
                'order_items': order.items.all(),
            })

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
        current_term = get_current_term()
        print('term', current_term)

        if current_term is None:
            messages.error(request, "We couldn't find an active term for this booking. Please try again later.")
            return redirect('shopping_cart:review_waiting_list_booking', swimling_id=swimling_id, product_id=product_id)

        # Use prorated price if term has started, otherwise full price
        total_price = lesson.get_prorated_price(current_term)

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

        # Check if payment is needed
        if total_price > 0:
            # Standard flow: redirect to BOIPA payment gateway
            order_ref = f"lesson_{order.id}"
            return redirect('boipa:initiate_payment_session', order_ref=order_ref, total_price=str(total_price))
        else:
            # Zero-balance flow: order fully paid (free or fully discounted)
            from lessons_orders.tasks import send_lesson_order_email
            order.paid = True
            order.save()
            handle_lessons_enrollment(order)
            send_lesson_order_email(order.id)

            return render(request, 'orders/order/created.html', {
                'order': order,
                'order_items': order.items.all(),
            })

    # Optionally handle GET requests or any other logic
    return redirect('shopping_cart:review_waiting_list_booking', swimling_id=swimling_id, product_id=product_id)
