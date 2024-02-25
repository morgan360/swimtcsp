from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from lessons.models import Product
from users.models import Swimling
from .cart import Cart
from .forms import CartAddProductForm
from users.forms import NewSwimlingForm
from django.contrib.auth.decorators import login_required

@login_required
@require_POST
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(user=request.user, data=request.POST)  # Corrected form instantiation
    if form.is_valid():
        cd = form.cleaned_data
        swimling = cd['swimling']
        cart.add(product=product, swimling=swimling)
        return redirect('lessons_cart:cart_detail')
    else:
        # Handle invalid form (optional: return an error message)
        return redirect('some_error_handling_view')


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('lessons_cart:cart_detail')


def cart_detail(request):
    cart = Cart(request)
    swimlings = []  # List to store retrieved swimling objects

    for item in cart:
        swimling_id = item['swimling']
        swimling = Swimling.objects.get(id=swimling_id)
        swimlings.append(swimling)  # Append retrieved swimling object to the list

        # You can also update the cart item with the retrieved swimling
        item['swimling'] = swimling

    return render(request, 'lessons_cart/detail.html', {'cart': cart, 'swimlings': swimlings})

