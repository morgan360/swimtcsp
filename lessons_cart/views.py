from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from lessons.models import Product
from users.models import Swimling
from .cart import Cart
from .forms import CartAddProductForm
from users.forms import NewSwimlingForm
from django.contrib.auth.decorators import login_required
from django.conf import settings
from decimal import Decimal
from django.contrib import messages

@login_required
@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(user=request.user, data=request.POST)

    if form.is_valid():
        swimling = form.cleaned_data['swimling']
        swimling_id = swimling.id

        # Call the add method with the correct parameters
        cart.add(product=product, swimling_id=swimling_id)

        messages.success(request, "Item successfully added to cart.")
        return redirect('lessons_cart:cart_detail')
    else:
        messages.error(request, "There was an error with your form submission.")
        return redirect('some_error_handling_view')


@login_required
@require_POST
def cart_remove(request, product_id, swimling_id):
    cart = Cart(request)
    try:
        # Assuming your cart uses a combined key for product and swimling or separate handling
        cart_key = f"{product_id}_{swimling_id}"
        cart.remove(cart_key)  # Updated remove function to accept the combined key
        messages.success(request, "Item removed from cart.")
    except KeyError:
        messages.error(request, "Item not found in cart.")
    return redirect('lessons_cart:cart_detail')

def cart_detail(request):
    cart = Cart(request)
    cart_items = []
    total_price = Decimal('0.00')  # Initialize total price

    for item_id, item_data in cart.cart.items():
        product_id, swimling_id = item_id.split('_')
        product = Product.objects.get(id=product_id)
        swimling = Swimling.objects.get(id=swimling_id)
        item_total = Decimal(item_data['price']) * item_data['quantity']
        total_price += item_total  # Update total price

        cart_items.append({
            'product_id': product_id,
            'product': product,
            'price': item_data['price'],
            'swimling': swimling,
            'total_price': item_total
        })

    return render(request, 'lessons_cart/detail.html', {'cart': cart_items, 'total_price': total_price})