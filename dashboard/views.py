# dashboard/views.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from swims.models import PublicSwimProduct

def is_admin(user):
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_admin)
def dashboard_home(request):
    return render(request, 'dashboard:dashboard/home.html')


@login_required
@user_passes_test(is_admin)
def public_swims(request):
    products = PublicSwimProduct.objects.select_related('category').only('name', 'category', 'slug').order_by('category__name', 'name')
    return render(request, 'dashboard/public_swims.html', {'products': products})


@login_required
@user_passes_test(is_admin)
def lessons(request):
    return render(request, 'dashboard/lessons.html')


@login_required
@user_passes_test(is_admin)
def schools(request):
    return render(request, 'dashboard/schools.html')


@login_required
@user_passes_test(is_admin)
def orders(request):
    return render(request, 'dashboard/orders.html')


@login_required
@user_passes_test(is_admin)
def general_admin(request):
    return render(request, 'dashboard/general.html')
