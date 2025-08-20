# dashboard/views.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.utils import timezone
from swims.models import PublicSwimProduct, PublicSwimCategory
from swims_orders.models import Order as SwimOrder

def is_admin(user):
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(is_admin)
def dashboard_home(request):
    # Get stats for the public swims card
    swim_stats = {
        'total_products': PublicSwimProduct.objects.count(),
        'active_products': PublicSwimProduct.objects.filter(available=True).count(),
        'categories_count': PublicSwimCategory.objects.count(),
        'recent_orders': SwimOrder.objects.filter(paid=True).order_by('-created')[:5],
        'today_orders_count': SwimOrder.objects.filter(
            created__date=timezone.now().date(),
            paid=True
        ).count()
    }
    
    context = {
        'swim_stats': swim_stats
    }
    
    return render(request, 'dashboard/home.html', context)


@login_required
@user_passes_test(is_admin)
def public_swims(request):
    # Get all products
    products = PublicSwimProduct.objects.all().prefetch_related('category')
    
    # Gather statistics
    stats = {
        'total_products': PublicSwimProduct.objects.count(),
        'active_products': PublicSwimProduct.objects.filter(available=True).count(),
        'categories': PublicSwimCategory.objects.all(),
        'recent_orders': SwimOrder.objects.select_related('product', 'user').order_by('-created')[:10],
    }
    
    return render(request, 'dashboard/public_swims.html', {
        'products': products,
        'stats': stats
    })


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
