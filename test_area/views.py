from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from lessons_cart.forms import CartAddProductForm
from lessons.models import Program, Category, Product
from django.core.paginator import Paginator


def t_lessons(request):
    days = Product.objects.values_list('day_of_week', flat=True).distinct()
    day_choices = [(day, dict(Product.DAY_CHOICES)[day]) for day in days]
    programs = Program.objects.all()
    active_lessons = Product.objects.filter(active=True, area_id=18)
    paginator = Paginator(active_lessons, 10)  # Show 10 lessons per page
    page_number = request.GET.get('page')  # Get the page number from the request
    page_obj = paginator.get_page(page_number)  # Get the page object

    return render(request, 't_lessons.html', {'page_obj': page_obj, 'programs': programs, 'days': day_choices})



def t_update_lesson_list(request):
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
    return render(request, 'partials/t_lesson_list.html', {'page_obj': page_obj,})


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    return render(request, 't_detail.html', {'product': product})
