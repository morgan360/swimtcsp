from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from swims.models import PublicSwimProduct, PublicSwimCategory
from swims_orders.models import Order as SwimOrder
from lessons.models import Program, Product
from lessons_bookings.models import LessonEnrollment
from instructors.models import InstructorAssignment
from django.contrib.auth import get_user_model
from datetime import timedelta, time as dt_time
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib import messages
from django.http import HttpResponseNotFound
from django.core.paginator import Paginator
from django.db.models import Q
from utils.context_processors import get_term_info
from utils.terms_utils import get_term_context_data

User = get_user_model()


def is_staff(user):
    return user.is_authenticated and user.is_staff


def is_superuser(user):
    return user.is_authenticated and user.is_superuser


def is_Manager(user):
    return user.is_authenticated and user.groups.filter(name='Manager').exists()


@login_required
@user_passes_test(is_staff)
def dashboard_home(request):
    swim_stats = {
        'total_products': PublicSwimProduct.objects.count(),
        'active_products': PublicSwimProduct.objects.filter(available=True).count(),
        'categories_count': PublicSwimCategory.objects.count(),
        'recent_orders': SwimOrder.objects.filter(paid=True).order_by('-created')[:5],
        'today_orders_count': SwimOrder.objects.filter(
            created__date=timezone.now().date(), paid=True
        ).count(),
    }
    return render(request, 'dashboard/home.html', {'swim_stats': swim_stats})


@login_required
@user_passes_test(is_staff)
def public_swims(request):
    products = PublicSwimProduct.objects.all().prefetch_related('category')
    stats = {
        'total_products': PublicSwimProduct.objects.count(),
        'active_products': PublicSwimProduct.objects.filter(available=True).count(),
        'categories': PublicSwimCategory.objects.all(),
        'recent_orders': SwimOrder.objects.select_related('product', 'user').order_by('-created')[:10],
    }
    return render(request, 'dashboard/public_swims.html', {'products': products, 'stats': stats})


@login_required
@user_passes_test(is_staff)
def lessons(request):
    return render(request, 'dashboard/lessons.html')


@login_required
@user_passes_test(is_staff)
def admin_lessons_list(request):
    term_data = get_term_context_data()
    phase = term_data['current_phase_id']
    term = term_data['next_term'] if phase == 'RB' else term_data['current_term']
    day_choices = Product.DAY_CHOICES
    programs = Program.objects.all()
    active_lessons = Product.objects.filter(active=True)

    selected_level = request.GET.get('level') or ''
    selected_day = request.GET.get('day') or ''
    selected_time = request.GET.get('time') or ''
    selected_availability = request.GET.get('availability') or ''

    if selected_level:
        try:
            active_lessons = active_lessons.filter(category_id=int(selected_level))
        except (TypeError, ValueError):
            pass
    if selected_day != '':
        try:
            active_lessons = active_lessons.filter(day_of_week=int(selected_day))
        except (TypeError, ValueError):
            pass
    if selected_time:
        try:
            h, m = selected_time.split(':')
            active_lessons = active_lessons.filter(start_time=dt_time(hour=int(h), minute=int(m)))
        except Exception:
            pass

    lessons_info = [
        {
            'lesson': lesson,
            'num_places': lesson.num_places,
            'remaining_spaces': lesson.remaining_spaces(term),
            'is_full': lesson.is_full(term),
        }
        for lesson in active_lessons
    ]

    if selected_availability == 'available':
        lessons_info = [li for li in lessons_info if not li['is_full']]
    elif selected_availability == 'full':
        lessons_info = [li for li in lessons_info if li['is_full']]

    paginator = Paginator(lessons_info, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    from lessons.models import Category
    categories = Category.objects.all().order_by('name')

    context = {
        'page_obj': page_obj,
        'programs': programs,
        'days': day_choices,
        'categories': categories,
        'times': sorted({lesson.start_time.strftime('%H:%M') for lesson in active_lessons if lesson.start_time}),
        'selected_level': selected_level,
        'selected_day': selected_day,
        'selected_time': selected_time,
        'selected_availability': selected_availability,
        'current_term': term,
        **get_term_info(request),
    }

    if request.headers.get('HX-Request'):
        return render(request, 'dashboard/_admin_lessons_list_content.html', context)
    return render(request, 'dashboard/admin_lessons_list.html', context)


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
def orders_history(request):
    """List swim orders with simple filters and pagination."""
    orders_qs = SwimOrder.objects.select_related('user', 'product').all()

    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()  # "paid" | "unpaid" | ""
    date_from = request.GET.get('from', '').strip()
    date_to = request.GET.get('to', '').strip()

    if q:
        orders_qs = orders_qs.filter(
            Q(txId__icontains=q)
            | Q(payment_status__icontains=q)
            | Q(user__email__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(product__name__icontains=q)
        )

    if status == 'paid':
        orders_qs = orders_qs.filter(paid=True)
    elif status == 'unpaid':
        orders_qs = orders_qs.filter(paid=False)

    # Date filtering (created date). Accepts YYYY-MM-DD
    try:
        if date_from:
            orders_qs = orders_qs.filter(created__date__gte=date_from)
        if date_to:
            orders_qs = orders_qs.filter(created__date__lte=date_to)
    except Exception:
        pass

    paginator = Paginator(orders_qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'q': q,
        'status': status,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'dashboard/orders_history.html', context)


@login_required
@user_passes_test(is_staff)
def general_admin(request):
    return render(request, 'dashboard/general.html', {})


@login_required
@user_passes_test(is_staff)
def user_management(request):
    context = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'new_users_month': User.objects.filter(date_joined__gte=timezone.now() - timedelta(days=30)).count(),
        'admin_users': User.objects.filter(is_staff=True).count(),
    }
    return render(request, 'dashboard/user_management.html', context)


@login_required
@user_passes_test(is_Manager)
def management(request):
    return render(request, 'dashboard/management.html', {})


@login_required
@user_passes_test(is_staff)
def user_list(request):
    users_query = User.objects.all().select_related().prefetch_related('groups')
    all_groups = Group.objects.all().order_by('name')
    all_permissions = Permission.objects.all().order_by('name')

    search = request.GET.get('search', '')
    if search:
        users_query = users_query.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(username__icontains=search)
        )

    status = request.GET.get('status', '')
    if status == 'active':
        users_query = users_query.filter(is_active=True)
    elif status == 'inactive':
        users_query = users_query.filter(is_active=False)

    role = request.GET.get('role', '')
    if role == 'admin':
        users_query = users_query.filter(is_superuser=True)
    elif role == 'staff':
        users_query = users_query.filter(is_staff=True, is_superuser=False)
    elif role == 'user':
        users_query = users_query.filter(is_staff=False, is_superuser=False)

    group_filter = request.GET.get('group', '')
    if group_filter:
        users_query = users_query.filter(groups__id=group_filter)

    permission_filter = request.GET.get('permission', '')
    if permission_filter:
        users_query = users_query.filter(user_permissions__id=permission_filter)

    users_query = users_query.order_by('-date_joined').distinct()
    paginator = Paginator(users_query, 25)
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
    is_guardian = forms.BooleanField(required=False)
    is_school = forms.BooleanField(required=False)

    class Meta:
        model = User
        fields = (
            'username', 'first_name', 'last_name', 'email',
            'password1', 'password2', 'is_active', 'is_staff', 'is_superuser',
        )


@login_required
@user_passes_test(is_staff)
def add_user(request):
    can_assign_groups = request.user.is_superuser or request.user.groups.filter(name__iexact='Manager').exists()

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        groups = request.POST.getlist('groups')
        wants_guardian = 'is_guardian' in request.POST
        wants_school = 'is_school' in request.POST

        if form.is_valid():
            user = form.save()

            if not request.user.is_superuser:
                user.is_staff = False
                user.is_superuser = False
                user.save()

            if can_assign_groups and groups:
                for group_id in groups:
                    try:
                        group = Group.objects.get(id=group_id)
                        user.groups.add(group)
                    except Group.DoesNotExist:
                        continue
            else:
                customer_group, _ = Group.objects.get_or_create(name='customer')
                user.groups.add(customer_group)

            if wants_guardian:
                guardian_group, _ = Group.objects.get_or_create(name='guardian')
                user.groups.add(guardian_group)
            if wants_school:
                schools_group, _ = Group.objects.get_or_create(name='schools')
                user.groups.add(schools_group)

            messages.success(request, f'User "{user.username}" created successfully.')
            return redirect('dashboard:user_list')
    else:
        form = CustomUserCreationForm()

    all_groups = Group.objects.all().order_by('name') if can_assign_groups else None
    return render(request, 'dashboard/add_user.html', {'form': form, 'all_groups': all_groups})


@login_required
@user_passes_test(lambda u: u.is_staff)
def edit_user(request, user_id):
    try:
        user_obj = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return HttpResponseNotFound("User not found")

    if request.method == 'GET':
        return render(request, 'dashboard/_edit_user_form.html', {'user_obj': user_obj})

    success = False
    errors = []
    try:
        user_obj.first_name = request.POST.get('first_name', '').strip()
        user_obj.last_name = request.POST.get('last_name', '').strip()
        user_obj.email = request.POST.get('email', '').strip()
        user_obj.is_active = 'is_active' in request.POST

        if not user_obj.email:
            errors.append('Email is required')
        elif User.objects.filter(email=user_obj.email).exclude(id=user_obj.id).exists():
            errors.append('Email already exists')

        if not errors:
            user_obj.save()
            success = True
            messages.success(request, f'User "{user_obj.get_full_name() or user_obj.email}" updated successfully.')
            user_obj.refresh_from_db()
    except Exception as e:
        errors.append(str(e))

    return render(request, 'dashboard/_edit_user_form.html', {
        'user_obj': user_obj,
        'success': success,
        'errors': errors,
    })


@login_required
@user_passes_test(lambda u: u.is_staff)
def view_user_swimlings(request, user_id):
    try:
        user_obj = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return HttpResponseNotFound("User not found")

    is_guardian = user_obj.groups.filter(name='guardian').exists()
    swimlings = []
    try:
        if hasattr(user_obj, 'swimlings'):
            swimlings = user_obj.swimlings.all()
        elif hasattr(user_obj, 'swimling_set'):
            swimlings = user_obj.swimling_set.all()
        elif hasattr(user_obj, 'children'):
            swimlings = user_obj.children.all()
    except Exception:
        swimlings = []

    context = {
        'user_obj': user_obj,
        'is_guardian': is_guardian,
        'swimlings': swimlings,
        'swimling_count': len(swimlings) if swimlings else 0,
    }
    return render(request, 'dashboard/_view_swimlings_modal.html', context)


@login_required
@user_passes_test(is_staff)
def lessons_history(request, lesson_id):
    lesson = get_object_or_404(Product, pk=lesson_id)
    today = timezone.localdate()
    instructor = getattr(lesson, "instructor", None)

    enrollments = (
        LessonEnrollment.objects
        .select_related("term", "swimling", "lesson")
        .filter(lesson=lesson)
        .order_by("term__start_date", "swimling__last_name", "swimling__first_name")
    )

    by_term = {}
    for enr in enrollments:
        term_obj = getattr(enr, "term", None)
        by_term.setdefault(term_obj, []).append(enr)

    def term_dates(term_obj):
        start_date = getattr(term_obj, "start_date", None)
        end_date = getattr(term_obj, "end_date", None)
        return start_date, end_date

    current_data, previous_data, upcoming_data = [], [], []

    for term_obj, term_enrollments in by_term.items():
        roster = []
        seen_ids = set()
        for e in term_enrollments:
            sl = getattr(e, "swimling", None)
            if sl:
                sid = getattr(sl, "id", None)
                if sid is None or sid not in seen_ids:
                    roster.append(sl)
                    if sid is not None:
                        seen_ids.add(sid)

        try:
            assignment = (
                InstructorAssignment.objects.select_related("instructor").filter(lesson=lesson, term=term_obj).first()
            )
            instructor = assignment.instructor if assignment else getattr(lesson, "instructor", None)
        except Exception:
            instructor = getattr(lesson, "instructor", None)
        capacity = getattr(lesson, "num_places", None)
        try:
            remaining = lesson.remaining_spaces(term_obj) if term_obj else None
        except Exception:
            remaining = None
        try:
            full_flag = lesson.is_full(term_obj) if term_obj else False
        except Exception:
            full_flag = False

        entry = {
            "term": term_obj,
            "instructor": instructor,
            "roster": roster,
            "attendance": [],
            "capacity": capacity,
            "remaining": remaining,
            "is_full": full_flag,
        }

        start_date = getattr(term_obj, "start_date", None)
        end_date = getattr(term_obj, "end_date", None)

        if start_date and start_date > today:
            upcoming_data.append(entry)
        elif start_date and end_date and start_date <= today <= end_date:
            current_data.append(entry)
        elif end_date and end_date < today:
            previous_data.append(entry)
        else:
            if start_date and start_date > today:
                upcoming_data.append(entry)
            else:
                previous_data.append(entry)

    def sort_key(item):
        start_date, end_date = term_dates(item["term"])
        return (end_date or today, start_date or today)

    current_data.sort(key=sort_key)
    previous_data.sort(key=sort_key, reverse=True)

    context = {
        "lesson": lesson,
        "current_data": current_data,
        "previous_data": previous_data,
    }
    return render(request, "dashboard/lessons_history.html", context)
