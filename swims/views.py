from django.shortcuts import render, redirect, get_object_or_404
from swims_cart.forms import CartAddProductForm
from .models import PublicSwimCategory, PublicSwimProduct, PriceVariant
from django.utils import timezone
from datetime import timedelta
from utils.date_utils import get_next_occurrence
from django.urls import reverse
import time
from .forms import ParticipantQuantityForm
# Assume a function to create BOIPA payment session, replace with your actual function
from boipa.views import initiate_boipa_payment_session
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
    product = get_object_or_404(PublicSwimProduct, id=id, slug=slug, available=True)
    price_variants = PriceVariant.objects.filter(product=product)
    quantities = range(1, 11)  # Assuming you allow up to 10 of each variant

    if request.method == 'POST':
        # Calculate total amount based on selected quantities and variant prices
        total_amount = 0
        for variant in price_variants:
            quantity = int(request.POST.get(f'quantity_{variant.id}', 0))
            total_amount += quantity * variant.price

        # Generate a unique order reference
        timestamp = time.strftime("%Y%m%d%H%M%S")
        order_ref = f"{product.slug}_{timestamp}"

        # Redirect to payment initiation with total amount and order reference
        return redirect(reverse('boipa:initiate_payment_session', kwargs={'order_ref': order_ref, 'total_price': str(total_amount)}))

    context = {
        'product': product,
        'price_variants': price_variants,
        'quantities': quantities,
    }
    return render(request, 'swims/product/detail.html', context)


