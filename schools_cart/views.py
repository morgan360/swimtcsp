from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from schools.models import ScoLessons
from users.models import Swimling
from .cart import Cart
from .forms import CartAddProductForm, NewSwimlingForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal
from django.http import Http404
import logging
# Create a logger object
logger = logging.getLogger('cart')


@login_required
@require_POST
def cart_add(request, product_id):
    logger.debug(f"Attempting to add product {product_id} to the cart for user {request.user.id}")
    cart = Cart(request)
    try:
        # Assuming you are fetching an ID from the request to query the database
        # product_id = request.GET.get('product_id')  # or another way you might be getting the product ID
        logger.debug(f"Attempting to retrive product {product_id} from ScoLessons")
        product = ScoLessons.objects.get(id=product_id)
    except ScoLessons.DoesNotExist:
        # Log the error and handle it
        logger.error(f"Product with ID {product_id} not found.")
        raise Http404("Product not found")
    except ValueError:
        # This handles cases where the product_id is None or an invalid integer
        logger.error("Invalid product ID provided.")
        raise Http404("Invalid product ID")

    form = CartAddProductForm(user=request.user, data=request.POST)

    if form.is_valid():
        swimling = form.cleaned_data['swimling']
        swimling_id = swimling.id
        cart.add(product=product, swimling_id=swimling_id)
        logger.info(f"Product {product_id} added to cart for swimling {swimling_id}")
        messages.success(request, "Item successfully added to cart.")
        return redirect('schools_cart:cart_detail')
    else:
        logger.warning(f"Form submission failed while adding product {product_id} to cart for user {request.user.id}")
        messages.error(request, "There was an error with your form submission.")
        return redirect('some_error_handling_view')


def cart_detail(request):
    cart = Cart(request)  # Assuming Cart is a class managing the session cart
    cart_items = []
    total_price = Decimal('0.00')

    logger.debug("Compiling cart details.")

    for item_key, item_data in cart.cart.items():
        try:
            product_id, swimling_id = item_key.split('_')
        except ValueError:
            logger.error(f"Invalid cart item key format: {item_key}")
            continue

        if not swimling_id:
            logger.error(f"Swimling ID missing for cart item key {item_key}")
            continue

        product = get_object_or_404(ScoLessons, id=product_id)
        swimling = get_object_or_404(Swimling, id=swimling_id)
        item_total = Decimal(item_data['price']) * item_data['quantity']
        total_price += item_total

        cart_items.append({
            'product_id': product_id,
            'product': product,
            'swimling': swimling,
            'swimling_id': swimling_id,
            'price': item_data['price'],
            'total_price': item_total
        })

    logger.debug(f"Total price of the cart is {total_price}")
    return render(request, 'schools_cart/detail.html', {'cart': cart_items, 'total_price': total_price})


@login_required
@require_POST
def cart_remove(request, product_id, swimling_id=1):
    logger.debug(f"Attempting to remove product {product_id} with swimling {swimling_id} from cart.")
    cart = Cart(request)
    try:
        cart_key = f"{product_id}_{swimling_id}"
        cart.remove(cart_key)
        logger.info(f"Removed product {product_id} with swimling {swimling_id} from cart.")
        messages.success(request, "Item removed from cart.")
    except KeyError:
        logger.error(f"Failed to find product {product_id} with swimling {swimling_id} in cart to remove.")
        messages.error(request, "Item not found in cart.")
    return redirect('schools_cart:cart_detail')
