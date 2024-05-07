from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.http import JsonResponse
from users.forms import NewSwimlingForm
from shopping_cart.forms import CartAddProductForm
from .models import ScoProgram, ScoCategory, ScoLessons, ScoSchool
from users.models import Swimling
import django_filters
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Q
from .filters import LessonFilter


# Get Lesson list for public lessons  Active=1
def school_list(request):
    sco_filter = LessonFilter(request.GET, queryset=ScoLessons.objects.all())

    if request.headers.get('HX-Request'):  # Check for HTMX request
        # Return only the part of the page that contains the filtered results
        return render(request, 'schools/partials/_lesson_list.html', {
            'lessons': sco_filter.qs
        })

    # Return the full page for non-AJAX requests
    return render(request, 'schools/products/sco_lessons.html', {
        'form': sco_filter.form,
        'lessons': sco_filter.qs
    })


@login_required
def school_detail(request, pk):
    product = get_object_or_404(ScoLessons, pk=pk)
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
    return render(request, 'schools/success.html')


# Failure view
def swimling_failure(request):
    return render(request, 'schools/failure.html')


def load_new_swimling_form(request, product_slug):
    form = NewSwimlingForm()
    product = ScoLessons.get(slug=product_slug)  # Retrieve the product based on the slug
    return render(request, 'partials/new_swimling_form.html', {'form': form, 'product': product})



