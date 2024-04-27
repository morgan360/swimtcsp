from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from schools.models import ScoLessons
from users.models import Swimling
from .cart import Cart
from .forms import CartAddProductForm, NewSwimlingForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from decimal import Decimal


@login_required
@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(ScoLessons, id=product_id)
    form = CartAddProductForm(user=request.user, data=request.POST)

    if form.is_valid():
        swimling = form.cleaned_data['swimling']
        swimling_id = swimling.id

        # Call the add method with the correct parameters
        cart.add(product=product, swimling_id=swimling_id)

        messages.success(request, "Item successfully added to cart.")
        return redirect('schools_cart:cart_detail')
    else:
        messages.error(request, "There was an error with your form submission.")
        return redirect('some_error_handling_view')


def cart_detail(request):
    cart = Cart(request)  # Assuming Cart is a class managing the session cart
    cart_items = []
    total_price = Decimal('0.00')

    for item_key, item_data in cart.cart.items():
        product_id, swimling_id = item_key.split('_')

        if not swimling_id:
            # Log an error, handle the situation, or skip this item
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

    return render(request, 'schools_cart/detail.html', {'cart': cart_items, 'total_price': total_price})




@login_required
@require_POST
def cart_remove(request, product_id, swimling_id=1):
    cart = Cart(request)
    try:
        # Assuming your cart uses a combined key for product and swimling or separate handling
        cart_key = f"{product_id}_{swimling_id}"
        cart.remove(cart_key)  # Updated remove function to accept the combined key
        messages.success(request, "Item removed from cart.")
    except KeyError:
        messages.error(request, "Item not found in cart.")
    return redirect('schools_cart:cart_detail')