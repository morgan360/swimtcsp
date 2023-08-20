from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from lessons_cart.forms import CartAddProductForm
# from .forms import SwimlingSelectionForm
from .models import Category, Product


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
    return render(request,
                  'lessons/products/list.html',
                  {'category': category,
                   'categories': categories,
                   'products': products})


@login_required  # Apply the login_required decorator
def product_detail(request, id, slug):
    product = get_object_or_404(Product,
                                id=id,
                                slug=slug,
                                available=True)

    # Pass the user argument to the CartAddProductForm
    cart_product_form = CartAddProductForm(user=request.user)

    return render(request,
                  'lessons/products/detail.html',
                  {'product': product,
                   'cart_product_form': cart_product_form})

