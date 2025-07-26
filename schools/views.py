from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from shopping_cart.forms import CartAddProductForm
from users.models import Swimling
from .models import ScoProgram, ScoCategory, ScoLessons, ScoSchool
from .filters import LessonFilter

import django_filters

# -------------------------------
# 📋 Lesson List for Public Schools
# -------------------------------
def school_list(request):
    sco_filter = LessonFilter(request.GET, queryset=ScoLessons.objects.all())

    if request.headers.get('HX-Request'):
        return render(request, 'schools/partials/_lesson_list.html', {
            'lessons': sco_filter.qs
        })

    return render(request, 'schools/products/sco_lessons.html', {
        'form': sco_filter.form,
        'lessons': sco_filter.qs
    })


# ----------------------
# 📄 School Lesson Detail
# ----------------------
@login_required
def school_detail(request, pk):
    product = get_object_or_404(ScoLessons, pk=pk)
    cart_product_form = CartAddProductForm(user=request.user)
    swimlings = Swimling.objects.filter(guardian=request.user)

    return render(request, 'schools/products/detail.html', {
        'product': product,
        'cart_product_form': cart_product_form,
        'swimlings': swimlings,
    })


# -----------------------------------------
# 🔍 Optional: General Product Filter View
# -----------------------------------------
def product_list(request):
    filter = ProductFilter(request.GET, queryset=Product.objects.all())

    if 'clear_filters' in request.GET:
        filter = ProductFilter(queryset=Product.objects.all())

    return render(request, 'schools/products/list_filter.html', {'filter': filter})
