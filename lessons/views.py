from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from lessons_cart.forms import CartAddProductForm, NewSwimlingForm
# from .forms import SwimlingSelectionForm
from .models import Program, Category, Product
from users.models import Swimling
import django_filters
from .filters import ProductFilter
from django.core.paginator import Paginator
from django.http import HttpResponse

# Get Lesson list for public swims only Area _ID = 18 (Public) and Active=1
def lesson_list(request):
    days = Product.objects.values_list('day_of_week', flat=True).distinct()
    day_choices = [(day, dict(Product.DAY_CHOICES)[day]) for day in days]
    programs = Program.objects.all()
    active_lessons = Product.objects.filter(active=True, area_id=18)
    paginator = Paginator(active_lessons, 10)  # Show 10 lessons per page
    page_number = request.GET.get('page')  # Get the page number from the request
    page_obj = paginator.get_page(page_number)  # Get the page object

    return render(request, 'lessons/products/lessons.html', {'page_obj': page_obj, 'programs': programs,
                                                             'days': day_choices})


def update_lesson_list(request):
    program_id = request.GET.get('program')
    day = request.GET.get('day')

    # Initialize query
    query = Product.objects.filter(active=True, area_id=18)

    # Apply filters if valid values are provided
    if program_id not in [None, '', 'null', 'undefined']:
        try:
            program_id = int(program_id)
            query = query.filter(category__program_id=program_id)
        except ValueError:
            # Handle the error if program_id is not a valid integer
            pass

    if day not in [None, '', 'null', 'undefined']:
        try:
            day = int(day)
            query = query.filter(day_of_week=day)
        except ValueError:
            # Handle the error if day is not a valid integer
            pass

    # Execute the query
    active_lessons = query
    paginator = Paginator(active_lessons, 10)  # Show 10 lessons per page
    page_number = request.GET.get('page')  # Get the page number from the request
    page_obj = paginator.get_page(page_number)  # Get the page object
    return render(request, 'partials/lesson_list.html', {'page_obj': page_obj, })


@login_required
def product_detail(request, slug):
    form = NewSwimlingForm()
    product = get_object_or_404(Product, slug=slug)
    cart_product_form = CartAddProductForm(user=request.user)  # Instantiate the form
    return render(request, 'lessons/products/detail.html', {
        'product': product,
        'cart_product_form': cart_product_form,  'form' : form
    })

def product_list(request):
    filter = ProductFilter(request.GET, queryset=Product.objects.all())

    # Check if a "clear_filters" parameter is present in the request
    if 'clear_filters' in request.GET:
        filter = ProductFilter(queryset=Product.objects.all())  # Create a fresh filter without any filters applied

    return render(request, 'lessons/products/list_filter.html', {'filter': filter})

# views.py

def add_new_swimling(request):
    if request.method == 'POST':
        form = NewSwimlingForm(request.POST)
        if form.is_valid():
            new_swimling = form.save(commit=False)
            new_swimling.guardian = request.user
            new_swimling.save()
            msg = "New swimmer created successfully"
            # Return a success message or redirect
            return render(request,'partials/success.html', {'success_message': msg})
        else:
            # Return the form with errors
            msg = "Something went wrong"
            return render(request, 'partials/failure.html', {'failure_message': msg})

    # GET request handling if necessary
    form = NewSwimlingForm()
    return render(request, 'partials/new_swimling_form.htm', {'form': form})

def load_new_swimling_form(request, product_slug):
    form = NewSwimlingForm()
    product = Product.objects.get(slug=product_slug)  # Retrieve the product based on the slug
    return render(request, 'partials/new_swimling_form.html', {'form': form, 'product': product})

