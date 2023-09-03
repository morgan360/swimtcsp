from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from lessons_cart.forms import CartAddProductForm
# from .forms import SwimlingSelectionForm
from .models import Program, Category, Product
import django_filters
from .filters import ProductFilter

from django.shortcuts import render
from .filters import ProductFilter


def product_list(request):
    filter = ProductFilter(request.GET, queryset=Product.objects.all())

    # Check if a "clear_filters" parameter is present in the request
    if 'clear_filters' in request.GET:
        filter = ProductFilter(queryset=Product.objects.all())  # Create a fresh filter without any filters applied

    return render(request, 'lessons/products/list_filter.html', {'filter': filter})


def programs(request):
    programs = Program.objects.all()
    lessons = Product.objects.all()
    categories = Category.objects.all()
    context = {'programs': programs, 'lessons': lessons, 'categories': categories}  # Use 'programs' as the key
    return render(request, 'lessons/products/programs.html', context)


def category_list(request):
    program = request.GET.get('program')
    if program == '*':
        categories = Category.objects.all()
    else:
        categories = Category.objects.filter(program=program)
    lessons = Product.objects.filter(category__in=categories)
    context = {'categories': categories, 'lessons': lessons}
    return render(request, 'partials/categories.html', context)


# def lesson_list(request):
#     category = request.GET.get('category')
#     if category == '*':
#         lessons = Product.objects.all()
#     else:
#         lessons = Product.objects.filter(category=category)
#     context = {'lessons': lessons}
#     return render(request, 'partials/lessons.html', context)


# def product_list(request, category_slug=None):
#     category = None
#     categories = Category.objects.all()
#     products = Product.objects.filter(active=True)
#     if category_slug:
#         category = get_object_or_404(Category, slug=category_slug)
#         products = products.filter(category=category)
#     return render(request,
#                   'lessons/products/list.html',
#                   {'category': category,
#                    'categories': categories,
#                    'products': products})


@login_required  # Apply the login_required decorator
def product_detail(request, id, slug):
    product = get_object_or_404(Product,
                                id=id,
                                slug=slug,
                                active=True)

    # Pass the user argument to the CartAddProductForm
    cart_product_form = CartAddProductForm(user=request.user)

    return render(request,
                  'lessons/products/detail.html',
                  {'product': product,
                   'cart_product_form': cart_product_form})
