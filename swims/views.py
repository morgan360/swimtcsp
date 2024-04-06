from django.shortcuts import render, redirect, get_object_or_404
from swims_cart.forms import CartAddProductForm
from .models import PublicSwimCategory, PublicSwimProduct, PriceVariant
from swims_orders.models import Order, OrderItem
from django.utils import timezone
from datetime import timedelta
from utils.date_utils import get_next_occurrence
from django.urls import reverse
from django.contrib.auth.decorators import login_required
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

@login_required
def product_detail(request, id, slug):
    product = get_object_or_404(PublicSwimProduct, id=id, slug=slug, available=True)
    price_variants = PriceVariant.objects.filter(product=product)
    quantities = range(0, 6)  # Assuming you allow up to 10 of each variant

    if request.method == 'POST':
        # Calculate total amount based on selected quantities and variant prices
        total_amount = 0
        order_items = []
        for variant in price_variants:
            quantity = int(request.POST.get(f'quantity_{variant.id}', 0))
            if quantity > 0:
                total_amount += quantity * variant.price
                order_items.append((variant, quantity))

        if total_amount > 0:
            # Calculate the next occurrence date for the product
            today = timezone.now().date()
            next_occurrence_date = get_next_occurrence(product.day_of_week)

            # Create Order and OrderItem objects
            order = Order.objects.create(
                user=request.user,
                product=product,
                booking=next_occurrence_date,  # Save the next occurrence date to the booking field
                paid=False,
                amount = total_amount,
            )
            for variant, quantity in order_items:
                OrderItem.objects.create(order=order, variant=variant, quantity=quantity)

            # Generate a unique order reference using the order ID
            order_ref = order.id

            # Redirect to payment initiation with total amount and order reference
            return redirect(reverse('boipa:initiate_payment_session', kwargs={'order_ref': order_ref, 'total_price': str(total_amount)}))
        else:
            # Handle the case where no items are selected (e.g., show an error message)
            pass

    next_occurrence_date = get_next_occurrence(product.day_of_week)
    context = {
        'next_occurrence_date':next_occurrence_date,
        'product': product,
        'price_variants': price_variants,
        'quantities': quantities,
    }
    return render(request, 'swims/product/detail.html', context)


def calculate_total(request):
    print(request.POST)  # Add this to check what's being posted
    total = 0
    for key, value in request.POST.items():
        if key.startswith('quantity_'):
            variant_id = key.split('_')[1]
            quantity = int(value)
            variant = PriceVariant.objects.get(id=variant_id)
            total += variant.price * quantity

    context = {'total': total}
    return render(request, 'swims/partials/total_price.html', context)
