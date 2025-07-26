from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from lessons_bookings.models import Term
from shopping_cart.forms import CartAddProductForm
from users.models import Swimling
from .models import Program, Category, Product
from .filters import ProductFilter
from utils.context_processors import get_term_info
from utils.terms_utils import get_term_context_data
from utils.terms_utils import get_current_term

# -----------------------
# 🎯 Main Lesson List View
# -----------------------
def lesson_list(request):
    swimling_id = request.GET.get('swimling')
    selected_swimling = None

    if swimling_id:
        try:
            selected_swimling = Swimling.objects.get(id=swimling_id, guardian=request.user)
        except Swimling.DoesNotExist:
            selected_swimling = None

    term_data = get_term_context_data()
    phase = term_data['current_phase_id']
    term = term_data['next_term'] if phase == 'RB' else term_data['current_term']
    print(f"🗓️ Showing lessons for term {term.id} ({'next' if phase == 'RB' else 'current'})")
    day_choices = Product.DAY_CHOICES
    programs = Program.objects.all()
    active_lessons = Product.objects.filter(active=True)

    lessons_info = [
        {
            'lesson': lesson,
            'num_places': lesson.num_places,
            'remaining_spaces': lesson.remaining_spaces(term),
            'is_full': lesson.is_full(term)
        }
        for lesson in active_lessons
    ]

    paginator = Paginator(lessons_info, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'lessons/lesson_list.html', {
        'page_obj': page_obj,
        'programs': programs,
        'days': day_choices,
        'current_term': term,
        'selected_swimling': selected_swimling,
        **get_term_info(request),
    })

# -------------------------------
# 🔄 HTMX Update Filtered Lessons
# -------------------------------
def update_lesson_list(request):
    term_data = get_term_context_data()
    phase = term_data['current_phase_id']
    term = term_data['next_term'] if phase == 'RB' else term_data['current_term']

    program_id = request.GET.get('program')
    day = request.GET.get('day')

    query = Product.objects.filter(active=True)

    if program_id not in [None, '', 'null', 'undefined']:
        try:
            query = query.filter(category__program_id=int(program_id))
        except ValueError:
            print("Invalid program_id")

    if day not in [None, '', 'null', 'undefined']:
        try:
            query = query.filter(day_of_week=int(day))
        except ValueError:
            print("Invalid day")

    lessons_info = [
        {
            'lesson': lesson,
            'num_places': lesson.num_places,
            'remaining_spaces': lesson.remaining_spaces(term),
            'is_full': lesson.is_full(term)
        }
        for lesson in query
    ]

    paginator = Paginator(lessons_info, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'partials/lesson_list.html', {
        'page_obj': page_obj,
        'current_term': term,
    })


# ---------------------------
# 🧾 Product (Lesson) Detail
# ---------------------------
@login_required


def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    swimlings = Swimling.objects.filter(guardian=request.user)
    cart_product_form = CartAddProductForm(user=request.user)

    # ⬇️ Get swimling ID from query string
    swimling_id = request.GET.get('swimling')
    selected_swimling = None
    if swimling_id:
        try:
            selected_swimling = Swimling.objects.get(id=swimling_id, guardian=request.user)
        except Swimling.DoesNotExist:
            selected_swimling = None


    current_term = get_current_term()
    num_sold = product.get_num_sold(current_term) if current_term else 0
    num_left = product.get_num_left(current_term) if current_term else 0

    return render(request, 'lessons/products/detail.html', {
        'product': product,
        'cart_product_form': cart_product_form,
        'swimlings': swimlings,
        'selected_swimling': selected_swimling,  # 🔑 for use in template
        'num_sold': num_sold,
        'num_left': num_left,
    })



# ---------------------------------
# 🔍 List Products with Filtering UI
# ---------------------------------
def product_list(request):
    filter = ProductFilter(request.GET, queryset=Product.objects.all())

    if 'clear_filters' in request.GET:
        filter = ProductFilter(queryset=Product.objects.all())

    return render(request, 'lessons/products/list_filter.html', {
        'filter': filter,
    })
