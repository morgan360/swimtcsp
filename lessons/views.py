from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from shopping_cart.forms import CartAddProductForm
from users.forms import NewSwimlingForm
from django.template.loader import render_to_string
from django.http import JsonResponse
from .models import Program, Category, Product
from users.models import Swimling
import django_filters
from .filters import ProductFilter
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from utils.terms_utils import get_current_term

# Get Lesson list for (Public) and Active=1
def lesson_list(request):
    current_term = get_current_term()

    # Instead of querying the database for day values, use the DAY_CHOICES directly
    day_choices = Product.DAY_CHOICES
    programs = Program.objects.all()
    active_lessons = Product.objects.filter(active=True)


    lessons_info = []
    for lesson in active_lessons:
        lessons_info.append({
            'lesson': lesson,
            'num_places': lesson.num_places,
            'remaining_spaces': lesson.remaining_spaces(current_term),
            'is_full': lesson.is_full(current_term)
        })

    paginator = Paginator(lessons_info, 8)  # Show 8 lessons per page
    page_number = request.GET.get('page')  # Get the page number from the request
    page_obj = paginator.get_page(page_number)  # Get the page object

    return render(request, 'lessons/products/lessons.html', {
        'page_obj': page_obj,
        'programs': programs,
        'days': day_choices,
        'current_term': current_term,
    })


def update_lesson_list(request):
    current_term = get_current_term()

    program_id = request.GET.get('program')
    day = request.GET.get('day')

    # Debugging: Log the received parameters
    print(f"Received program_id: {program_id}, day: {day}")

    # Initialize query
    query = Product.objects.filter(active=True)

    # Apply filters if valid values are provided
    if program_id not in [None, '', 'null', 'undefined']:
        try:
            program_id = int(program_id)
            query = query.filter(category__program_id=program_id)
        except ValueError:
            # Handle the error if program_id is not a valid integer
            print("Invalid program_id")

    if day not in [None, '', 'null', 'undefined']:
        try:
            day = int(day)
            query = query.filter(day_of_week=day)
        except ValueError:
            # Handle the error if day is not a valid integer
            print("Invalid day")

    # Execute the query
    active_lessons = query

    lessons_info = []
    for lesson in active_lessons:
        lessons_info.append({
            'lesson': lesson,
            'num_places': lesson.num_places,
            'remaining_spaces': lesson.remaining_spaces(current_term),
            'is_full': lesson.is_full(current_term)
        })

    paginator = Paginator(lessons_info, 8)  # Show 8 lessons per page
    page_number = request.GET.get('page')  # Get the page number from the request
    page_obj = paginator.get_page(page_number)  # Get the page object

    return render(request, 'partials/lesson_list.html', {'page_obj': page_obj, 'current_term': current_term})

@login_required
def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    form = NewSwimlingForm()
    cart_product_form = CartAddProductForm(user=request.user)
    swimlings = Swimling.objects.filter(guardian=request.user)  # Assuming association via guardian

    return render(request, 'lessons/products/detail.html', {
        'product': product,
        'cart_product_form': cart_product_form,
        'form': form,
        'swimlings': swimlings,
    })


def product_list(request):
    filter = ProductFilter(request.GET, queryset=Product.objects.all())

    # Check if a "clear_filters" parameter is present in the request
    if 'clear_filters' in request.GET:
        filter = ProductFilter(queryset=Product.objects.all())  # Create a fresh filter without any filters applied

    return render(request, 'lessons/products/list_filter.html', {'filter': filter})

# Gives user the option to add new swimmer to portfolio
def add_new_swimling(request):
    if request.method == 'POST':
        form = NewSwimlingForm(request.POST)
        if form.is_valid():
            new_swimling = form.save(commit=False)
            new_swimling.guardian = request.user
            new_swimling.save()

            # Fetch updated swimlings for the dropdown
            swimlings = Swimling.objects.filter(guardian=request.user)
            # success message
            messages.success(request, 'Swimling added successfully.')
            # Render the partial template for the dropdown
            rendered_html = render_to_string('partials/swimlings_list.html', {'swimlings': swimlings},
                                             request=request)

            # Respond with the rendered HTML for HTMX to swap
            return HttpResponse(rendered_html)
        else:
            if "HX-Request" in request.headers:
                # If form is invalid during an HTMX request, return the form with errors
                context = {'form': form}
                html = render_to_string('partials/new_swimling_form.html', context, request=request)
                return HttpResponse(html, status=400)
            else:
                # For non-HTMX, render the form with errors within the context of a full page
                return render(request, 'partials/new_swimling_form.html', {'form': form})

    else:
        form = NewSwimlingForm()
        return render(request, 'partials/new_swimling_form.html', {'form': form})


# Success view
def swimling_success(request):
    return render(request, 'lessons/success.html')


# Failure view
def swimling_failure(request):
    return render(request, 'lessons/failure.html')


def load_new_swimling_form(request, product_slug):
    form = NewSwimlingForm()
    product = Product.objects.get(slug=product_slug)  # Retrieve the product based on the slug
    return render(request, 'partials/new_swimling_form.html', {'form': form, 'product': product})
