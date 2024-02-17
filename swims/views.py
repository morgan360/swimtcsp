from django.shortcuts import render, get_object_or_404
from swims_cart.forms import CartAddProductForm
from .models import PublicSwimCategory, PublicSwimProduct, PriceVariant
from django.utils import timezone
from datetime import timedelta
from utils.date_utils import get_next_occurrence

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


def product_detail(request, id, slug):
    product = get_object_or_404(PublicSwimProduct,
                                id=id,
                                slug=slug,
                                available=True)
    cart_product_form = CartAddProductForm()
    price_variants = PriceVariant.objects.filter(product=product)
    quantities = range(1, 11)
    context = {'product': product,
               'price_variants': price_variants,
               'cart_product_form': cart_product_form,
               'quantities': quantities,}
    return render(request,
                  'swims/product/detail.html',
                  context)

