from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from schools_cart.forms import CartAddProductForm, NewSwimlingForm
from django.template.loader import render_to_string
from django.http import JsonResponse
from .models import ScoProgram, ScoCategory, ScoLessons
from users.models import Swimling
import django_filters
from .filters import ProductFilter
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages


# Get Lesson list for public swims only Area _ID = 18 (Public) and Active=1
def school_list(request):
    days = ScoLessons.objects.values_list('day_of_week', flat=True).distinct()
    day_choices = [(day, dict(ScoLessons.DAY_CHOICES)[day]) for day in days]
    sco_programs = ScoProgram.objects.all()
    active_lessons = ScoLessons.objects.filter(active=True, area_id=18)
    paginator = Paginator(active_lessons,  8)  # Show 10 lessons per page
    page_number = request.GET.get('page')  # Get the page number from the request
    page_obj = paginator.get_page(page_number)  # Get the page object

    return render(request, 'schools/products/sco_lessons.html', {'page_obj': page_obj, 'programs':  sco_programs,
                                                             'days': day_choices})


def update_school_list(request):
    program_id = request.GET.get('program')
    day = request.GET.get('day')

    # Initialize query
    query = ScoLessons.objects.filter(active=True, area_id=18)

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
    paginator = Paginator(active_lessons, 8)  # Show 10 lessons per page
    page_number = request.GET.get('page')  # Get the page number from the request
    page_obj = paginator.get_page(page_number)  # Get the page object
    return render(request, 'partials/schools_list.html', {'page_obj': page_obj, })


@login_required
def school_detail(request, slug):
    product = get_object_or_404(ScoLessons, slug=slug)
    form = NewSwimlingForm()
    cart_product_form = CartAddProductForm(user=request.user)  # Instantiate the form
    swimlings = Swimling.objects.filter(guardian=request.user)  # Assuming association via guardian

    return render(request, 'schools/products/detail.html', {
        'product': product,
        'cart_product_form': cart_product_form,
        'form': form,
        'swimlings': swimlings,  # Pass swimlings to the template
    })


def product_list(request):
    filter = ProductFilter(request.GET, queryset=Product.objects.all())

    # Check if a "clear_filters" parameter is present in the request
    if 'clear_filters' in request.GET:
        filter = ProductFilter(queryset=Product.objects.all())  # Create a fresh filter without any filters applied

    return render(request, 'schools/products/list_filter.html', {'filter': filter})


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
    product = ScoLessons.get(slug=product_slug)  # Retrieve the product based on the slug
    return render(request, 'partials/new_swimling_form.html', {'form': form, 'product': product})
