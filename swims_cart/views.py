from django.shortcuts import render, redirect, get_object_or_404
from swims.models import PublicSwimProduct, PriceVariant
from .cart import Cart
from .forms import CartAddProductForm
from django.urls import reverse
from utils.date_utils import get_next_occurrence
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect

def add_to_cart(request, product_id):
    cart = Cart(request)
    variation_list = []
    quantity_list = []
    # Get the product queryset
    product = get_object_or_404(PublicSwimProduct, id=product_id)
    for variation in product.price_variants.all():
        quantity_str = request.POST.get(f'quantity_{variation.id}')
        if quantity_str is not None:
            try:
                quantity = int(quantity_str)
            except ValueError:
                # Handle the case where the quantity is not a valid integer
                return HttpResponseBadRequest(f"Invalid quantity for variation {variation.id}.")
            if quantity > 0:
                variation_id = variation.id  # Directly use variation.id since it's already an int
                variation_list.append(variation_id)
                quantity_list.append(quantity)
        # Optionally, handle the case where quantity_str is None
        # For example, skip adding this variation or set a default quantity
    next_occurrence = get_next_occurrence(product.day_of_week)
    cart.add(product.id, variation_list, quantity_list, next_occurrence)
    return redirect('swims_cart:cart_detail')



def remove_from_cart(request, product_id):
    cart = Cart(request)
    cart.remove(product_id)
    return redirect('swims_cart:cart_detail')


def update_cart(request):
    cart = Cart(request)
    for item in cart.cart:
        quantity = int(request.POST.get(str(item['product'].id)))
        cart.update(item['product'].id, quantity)
    return redirect('cart')


def view_cart(request):
    cart = Cart(request)
    return render(request, 'cart.html', {'cart': cart})


def cart_detail(request):
    cart = Cart(request)
    context = cart.cart_retrieve()
    return render(request, 'cart_detail.html', context)


def clear_cart(request):
    cart = Cart(request)
    cart.clear_cart()
    return redirect('home')

