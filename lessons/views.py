from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q
from lessons_bookings.models import Term
from shopping_cart.forms import CartAddProductForm
from users.models import Swimling
from .models import Program, Category, Product
from .filters import ProductFilter
from utils.context_processors import get_term_info
from utils.terms_utils import get_term_context_data
from utils.terms_utils import get_current_term

# HELPERS
import re

LEVEL_ORDER = [
    "Beginners 1", 
    "Beginners 2",
    "Improvers 1", 
    "Improvers 2",
    "Advanced",
    "Lengths L1", 
    "Lengths L2", 
    "Lengths L3",
]

def _split_multi(value_list):
    """
    Accepts a list of values that may contain comma-separated items and
    returns a flat, stripped list.
    """
    out = []
    for v in value_list:
        if v is None:
            continue
        parts = [p.strip() for p in str(v).split(",") if p.strip()]
        out.extend(parts)
    return out

def _normalize_level(label: str) -> str | None:
    """Map common variants to canonical LEVEL_ORDER names."""
    if not label:
        return None
    s = re.sub(r"\s+", " ", label).strip().lower()

    # exact buckets
    if re.search(r"^beg(inner)?s?\s*1\b|^b1\b", s): return "Beginners 1"
    if re.search(r"^beg(inner)?s?\s*2\b|^b2\b", s): return "Beginners 2"
    if re.search(r"^imp(rover)?s?\s*1\b|^i1\b", s): return "Improvers 1"
    if re.search(r"^imp(rover)?s?\s*2\b|^i2\b", s): return "Improvers 2"
    if re.search(r"^adv", s):                       return "Advanced"
    if re.search(r"(lengths?|l)\s*(l?\s*1|\b1\b)", s): return "Lengths L1"
    if re.search(r"(lengths?|l)\s*(l?\s*2|\b2\b)", s): return "Lengths L2"
    if re.search(r"(lengths?|l)\s*(l?\s*3|\b3\b)", s): return "Lengths L3"
    return None

def _level_keywords(level: str) -> dict:
    """
    Return keywords for fuzzy matching across name/short_name/product name.
    """
    level = (level or "").lower()
    if level.startswith("advanced"):
        return {"tokens_any": [["adv", "advanced"]], "numbers": []}

    if level.startswith("beginners 1"):
        return {"tokens_any": [["beg", "beginner", "beginners"]], "numbers": ["1"]}
    if level.startswith("beginners 2"):
        return {"tokens_any": [["beg", "beginner", "beginners"]], "numbers": ["2"]}

    if level.startswith("improvers 1"):
        return {"tokens_any": [["imp", "improver", "improvers"]], "numbers": ["1"]}
    if level.startswith("improvers 2"):
        return {"tokens_any": [["imp", "improver", "improvers"]], "numbers": ["2"]}

    if level.startswith("lengths l1"):
        return {"tokens_any": [["len", "length", "lengths"]], "numbers": ["1", "l1"]}
    if level.startswith("lengths l2"):
        return {"tokens_any": [["len", "length", "lengths"]], "numbers": ["2", "l2"]}
    if level.startswith("lengths l3"):
        return {"tokens_any": [["len", "length", "lengths"]], "numbers": ["3", "l3"]}

    # Fallback – try to split "word number"
    parts = level.split()
    nums = [p for p in parts if p.replace("l", "").isdigit() or p in ("l1","l2","l3")]
    toks = [[p] for p in parts if not p.replace("l", "").isdigit()]
    return {"tokens_any": toks or [[level]], "numbers": nums}

def _level_q(norm_level: str) -> Q:
    """
    Build a Q that matches:
      - category.name icontains tokens AND numbers
      - OR category.short_name icontains tokens AND numbers
      - OR product.name icontains tokens AND numbers
    'Advanced' has no numbers.
    """
    kw = _level_keywords(norm_level)

    # fields we want to search
    fields = ["category__name", "category__short_name", "name"]

    # For each field, require all pieces for that field (tokens + numbers)
    per_field_qs = []
    for f in fields:
        qf = Q()
        # at least one of the token variants (e.g., beg|beginner|beginners)
        for token_group in kw["tokens_any"]:
            # each token_group is alternatives; match any of them for this field
            alt_q = Q()
            for t in token_group:
                alt_q |= Q(**{f + "__icontains": t})
            qf &= alt_q
        # and include all numeric markers (e.g., "1" and/or "l1")
        for n in kw["numbers"]:
            qf &= Q(**{f + "__icontains": n})
        per_field_qs.append(qf)

    # Match if any field matches
    combined = Q()
    for q in per_field_qs:
        combined |= q
    return combined

# -----------------------
# 🎯 Main Lesson List View
# -----------------------
@login_required
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

    day_choices = Product.DAY_CHOICES
    programs = Program.objects.all()

    # ----------------------------
    # 🔎 Read & normalize filters
    # ----------------------------
    raw_days = _split_multi(request.GET.getlist('day'))       # e.g. ['1','3']
    raw_levels = _split_multi(request.GET.getlist('level'))   # e.g. ['Beginners 1','Improvers 2']

    # Cast days to ints where possible
    selected_days: list[int] = []
    for d in raw_days:
        try:
            selected_days.append(int(d))
        except (TypeError, ValueError):
            pass

    # Normalize levels to canonical names
    selected_levels = []
    for lv in raw_levels:
        norm = _normalize_level(lv)
        if norm:
            selected_levels.append(norm)

    # ----------------------------
    # 📦 Build queryset with filters
    # ----------------------------
    query = Product.objects.filter(active=True)

    if selected_days:
        query = query.filter(day_of_week__in=selected_days)

    if selected_levels:
        lvl_q = Q()
        for lvl in selected_levels:
            lvl_q |= _level_q(lvl)
        query = query.filter(lvl_q)

    # ----------------------------
    # 🧮 Build lesson info + paginate
    # ----------------------------
    lessons_info = [
        {
            'lesson': lesson,
            'num_places': lesson.num_places,
            'remaining_spaces': lesson.remaining_spaces(term),
            'is_full': lesson.is_full(term),
        }
        for lesson in query
    ]

    return render(request, 'lessons/lesson_list.html', {
        'lessons_info': lessons_info,
        'programs': programs,
        'days': day_choices,
        'levels': LEVEL_ORDER,                  # 👈 expose levels to the template
        'selected_days': selected_days,         # for keeping filter UI state
        'selected_levels': selected_levels,     # for keeping filter UI state
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

    # 🔎 Read filters
    raw_days = _split_multi(request.GET.getlist('day'))
    raw_levels = _split_multi(request.GET.getlist('level'))

    selected_days: list[int] = []
    for d in raw_days:
        try:
            selected_days.append(int(d))
        except (TypeError, ValueError):
            pass

    selected_levels = []
    for lv in raw_levels:
        norm = _normalize_level(lv)
        if norm:
            selected_levels.append(norm)

    # Build queryset
    query = Product.objects.filter(active=True)

    if program_id not in [None, '', 'null', 'undefined']:
        try:
            query = query.filter(category__program_id=int(program_id))
        except ValueError:
            print("Invalid program_id")

    if selected_days:
        query = query.filter(day_of_week__in=selected_days)

    if selected_levels:
        lvl_q = Q()
        for lvl in selected_levels:
            lvl_q |= _level_q(lvl)
        query = query.filter(lvl_q)

    # Build lesson info without pagination so all lessons are returned
    lessons_info = [
        {
            'lesson': lesson,
            'num_places': lesson.num_places,
            'remaining_spaces': lesson.remaining_spaces(term),
            'is_full': lesson.is_full(term),
        }
        for lesson in query
    ]

    return render(request, 'partials/lesson_list.html', {
        'lessons_info': lessons_info,
        'current_term': term,
        'selected_days': selected_days,       # useful if the partial shows active filters
        'selected_levels': selected_levels,   # idem
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

    term_data = get_term_context_data()
    phase = term_data['current_phase_id']
    selected_term = term_data['next_term'] if phase in ['RB', 'BN'] else term_data['current_term']

    num_sold = product.get_num_sold(selected_term) if selected_term else 0
    num_left = product.get_num_left(selected_term) if selected_term else 0

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
