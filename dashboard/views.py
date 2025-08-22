# dashboard/views.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.utils import timezone
from swims.models import PublicSwimProduct, PublicSwimCategory
from swims_orders.models import Order as SwimOrder
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib import messages
from django.http import HttpResponseNotFound
from django.core.paginator import Paginator
from django.db.models import Q

User = get_user_model()

def is_staff(user):
    return user.is_authenticated and user.is_staff

def is_superuser(user):
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(is_staff)
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
@user_passes_test(is_staff)
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
@user_passes_test(is_staff)
def lessons(request):
    return render(request, 'dashboard/lessons.html')


@login_required
@user_passes_test(is_staff)
def schools(request):
    return render(request, 'dashboard/schools.html')


@login_required
@user_passes_test(is_staff)
def orders(request):
    return render(request, 'dashboard/orders.html')


@login_required
@user_passes_test(is_staff)
def general_admin(request):
    return render(request, 'dashboard/general.html', context)


@login_required
@user_passes_test(is_staff)
def user_management(request):
    """User management dashboard page"""
    context = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'new_users_month': User.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=30)
        ).count(),
        'admin_users': User.objects.filter(is_staff=True).count(),
    }
    return render(request, 'dashboard/user_management.html', context)


@login_required
@user_passes_test(is_superuser)
def management(request):
    """System management dashboard page - Superuser access only"""
    context = {
        # Add any system status or configuration data here
    }
    return render(request, 'dashboard/management.html', context)


@login_required
@user_passes_test(is_staff)
def user_list(request):
    """User list page with search and filtering"""
    users_query = User.objects.all().select_related().prefetch_related('groups')
    
    # Get all groups and permissions for dynamic filtering
    all_groups = Group.objects.all().order_by('name')
    all_permissions = Permission.objects.all().order_by('name')
    
    # Search functionality
    search = request.GET.get('search', '')
    if search:
        users_query = users_query.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(username__icontains=search)
        )
    
    # Status filter
    status = request.GET.get('status', '')
    if status == 'active':
        users_query = users_query.filter(is_active=True)
    elif status == 'inactive':
        users_query = users_query.filter(is_active=False)
    
    # Role filter
    role = request.GET.get('role', '')
    if role == 'admin':
        users_query = users_query.filter(is_superuser=True)
    elif role == 'staff':
        users_query = users_query.filter(is_staff=True, is_superuser=False)
    elif role == 'user':
        users_query = users_query.filter(is_staff=False, is_superuser=False)
    
    # Group filter
    group_filter = request.GET.get('group', '')
    if group_filter:
        users_query = users_query.filter(groups__id=group_filter)
    
    # Permission filter
    permission_filter = request.GET.get('permission', '')
    if permission_filter:
        users_query = users_query.filter(user_permissions__id=permission_filter)
    
    # Order by
    users_query = users_query.order_by('-date_joined').distinct()
    
    # Pagination
    paginator = Paginator(users_query, 25)  # Show 25 users per page
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)
    
    context = {
        'users': users,
        'search': search,
        'all_groups': all_groups,
        'all_permissions': all_permissions,
    }
    return render(request, 'dashboard/user_list.html', context)


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    is_active = forms.BooleanField(required=False, initial=True)
    is_staff = forms.BooleanField(required=False)
    is_superuser = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser')


@login_required
@user_passes_test(is_staff)
def add_user(request):
    """Add new user page"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        groups = request.POST.getlist('groups')
        
        if form.is_valid():
            user = form.save()
            
            # Only allow superusers to set staff/superuser status
            if not request.user.is_superuser:
                user.is_staff = False
                user.is_superuser = False
                user.save()
            
            # Assign groups
            if request.user.is_superuser and groups:
                # Superuser can assign specific groups
                for group_id in groups:
                    try:
                        group = Group.objects.get(id=group_id)
                        user.groups.add(group)
                    except Group.DoesNotExist:
                        pass
            else:
                # All new users get 'customer' group by default
                try:
                    customer_group = Group.objects.get(name='customer')
                    user.groups.add(customer_group)
                except Group.DoesNotExist:
                    # Create customer group if it doesn't exist
                    customer_group = Group.objects.create(name='customer')
                    user.groups.add(customer_group)
            
            messages.success(request, f'User "{user.username}" has been created successfully and assigned to customer group.')
            return redirect('dashboard:user_list')
    else:
        form = CustomUserCreationForm()
    
    # Get all groups for selection (only for superusers)
    all_groups = Group.objects.all().order_by('name') if request.user.is_superuser else None
    
    context = {
        'form': form,
        'all_groups': all_groups,
    }
    return render(request, 'dashboard/add_user.html', context)


@login_required
@user_passes_test(is_staff)
def dashboard_users(request):
    """User management dashboard page"""
    context = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'new_users_month': User.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=30)
        ).count(),
        'admin_users': User.objects.filter(is_staff=True).count(),
    }
    return render(request, 'dashboard/user_management.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def edit_user(request, user_id):
    """Edit user details - available to staff members"""
    try:
        user_obj = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return HttpResponseNotFound("User not found")
    
    if request.method == 'GET':
        # Return the form
        context = {
            'user_obj': user_obj,
        }
        return render(request, 'dashboard/_edit_user_form.html', context)
    
    elif request.method == 'POST':
        # Process the form
        success = False
        errors = []
        
        try:
            # Update user fields
            user_obj.first_name = request.POST.get('first_name', '').strip()
            user_obj.last_name = request.POST.get('last_name', '').strip()
            user_obj.email = request.POST.get('email', '').strip()
            user_obj.is_active = 'is_active' in request.POST
            
            # Validate email
            if not user_obj.email:
                errors.append("Email is required")
            elif User.objects.filter(email=user_obj.email).exclude(id=user_obj.id).exists():
                errors.append("Email already exists")
            
            if not errors:
                user_obj.save()
                success = True
                messages.success(request, f'User "{user_obj.get_full_name() or user_obj.email}" updated successfully.')
                
                # Refresh user object to get updated data
                user_obj.refresh_from_db()
        
        except Exception as e:
            errors.append(str(e))
        
        context = {
            'user_obj': user_obj,
            'success': success,
            'errors': errors,
        }
        return render(request, 'dashboard/_edit_user_form.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff)
def view_user_swimlings(request, user_id):
    """View swimlings for a specific user - available to staff members"""
    try:
        user_obj = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return HttpResponseNotFound("User not found")
    
    # Check if user is in guardian group
    is_guardian = user_obj.groups.filter(name='guardian').exists()
    
    # Get swimlings - try different possible relationships
    swimlings = []
    try:
        # Try the most common relationship name
        if hasattr(user_obj, 'swimlings'):
            swimlings = user_obj.swimlings.all()
        # Try alternative relationship names
        elif hasattr(user_obj, 'swimling_set'):
            swimlings = user_obj.swimling_set.all()
        elif hasattr(user_obj, 'children'):
            swimlings = user_obj.children.all()
        else:
            # Import the model directly and try a reverse lookup
            try:
                from swimling_dashboard.models import Swimling
                swimlings = Swimling.objects.filter(guardian=user_obj)
            except ImportError:
                pass
    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching swimlings for user {user_id}: {e}")
        swimlings = []
    
    context = {
        'user_obj': user_obj,
        'is_guardian': is_guardian,
        'swimlings': swimlings,
        'swimling_count': len(swimlings) if swimlings else 0,
    }
    return render(request, 'dashboard/_view_swimlings_modal.html', context)
