from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from swims.models import PublicSwimProduct, PublicSwimCategory
from swims_orders.models import Order as SwimOrder
from lessons_orders.models import Order as LessonOrder
from schools_orders.models import Order as SchoolOrder
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
from django.db.models import Q, Sum
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

    paginator = Paginator(lessons_info, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    from lessons.models import Category
    categories = Category.objects.all().order_by('name')

    context = {
        'page_obj': page_obj,
        'total': paginator.count,
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
def admin_lessons_list_rows(request):
    """Return paginated HTML fragments for admin lessons list (rows or cards)."""
    term_data = get_term_context_data()
    phase = term_data['current_phase_id']
    term = term_data['next_term'] if phase == 'RB' else term_data['current_term']

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

    paginator = Paginator(lessons_info, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    variant = request.GET.get('variant', 'desktop')
    template_name = 'dashboard/_admin_lesson_rows.html' if variant == 'desktop' else 'dashboard/_admin_lesson_cards.html'

    html = render(request, template_name, {
        'page_obj': page_obj,
    }).content.decode('utf-8')

    from django.http import JsonResponse
    return JsonResponse({
        'html': html,
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        'count_this_page': len(page_obj.object_list),
    })


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
    """List ALL orders (swims, lessons, schools) with filters + pagination.
    Includes monthly stats cards for management users.
    """
    # Monthly stats (visible only to superusers or Manager group)
    order_stats = None
    try:
        if request.user.is_superuser or is_Manager(request.user):
            now = timezone.now()
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # first day of next month
            if month_start.month == 12:
                next_month_start = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month_start = month_start.replace(month=month_start.month + 1)

            swims_m = SwimOrder.objects.filter(created__gte=month_start, created__lt=next_month_start)
            lessons_m = LessonOrder.objects.filter(created__gte=month_start, created__lt=next_month_start)
            schools_m = SchoolOrder.objects.filter(created__gte=month_start, created__lt=next_month_start)

            def qs_count(qs):
                return qs.count()

            def qs_sum_amount(qs):
                total = qs.aggregate(total=Sum('amount'))['total']
                return total or 0

            def qs_paid_count(qs):
                return qs.filter(paid=True).count()

            order_stats = {
                'month_label': now.strftime('%B %Y'),
                'total_orders': qs_count(swims_m) + qs_count(lessons_m) + qs_count(schools_m),
                'paid_orders': qs_paid_count(swims_m) + qs_paid_count(lessons_m) + qs_paid_count(schools_m),
                'unpaid_orders': (
                    (qs_count(swims_m) - qs_paid_count(swims_m)) +
                    (qs_count(lessons_m) - qs_paid_count(lessons_m)) +
                    (qs_count(schools_m) - qs_paid_count(schools_m))
                ),
                'revenue_total': qs_sum_amount(swims_m) + qs_sum_amount(lessons_m) + qs_sum_amount(schools_m),
                'revenue_swims': qs_sum_amount(swims_m),
                'revenue_lessons': qs_sum_amount(lessons_m),
                'revenue_schools': qs_sum_amount(schools_m),
            }

            paid_total = (
                qs_sum_amount(swims_m.filter(paid=True)) +
                qs_sum_amount(lessons_m.filter(paid=True)) +
                qs_sum_amount(schools_m.filter(paid=True))
            )
            paid_count = qs_paid_count(swims_m) + qs_paid_count(lessons_m) + qs_paid_count(schools_m)
            all_count = order_stats['total_orders'] or 1
            order_stats['avg_order_value_paid'] = (paid_total / paid_count) if paid_count else 0
            order_stats['avg_order_value_overall'] = (order_stats['revenue_total'] / all_count) if all_count else 0
    except Exception:
        order_stats = None
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()  # "paid" | "unpaid" | ""
    category = request.GET.get('category', '').strip()  # "swims" | "lessons" | "schools" | ""
    date_from = request.GET.get('from', '').strip()
    date_to = request.GET.get('to', '').strip()

    # Fetch per source
    swims = (
        SwimOrder.objects.select_related('user', 'product')
        .all()
    )
    lessons = (
        LessonOrder.objects.select_related('user')
        .prefetch_related('items__product', 'items__term')
        .all()
    )
    schools = (
        SchoolOrder.objects.select_related('user', 'school')
        .prefetch_related('items__product', 'items__term')
        .all()
    )

    def normalize_swim(o):
        product_name = getattr(getattr(o, 'product', None), 'name', None)
        booking = getattr(o, 'booking', None)
        context = f"{product_name or ''} {booking or ''}".strip()
        return {
            'id': o.id,
            'created': o.created,
            'user_full': o.user.get_full_name() or o.user.email,
            'user_email': o.user.email,
            'amount': o.amount,
            'paid': o.paid,
            'txId': o.txId,
            'payment_status': o.payment_status,
            'type': 'Public Swim',
            'category': 'swims',
            'context': context or '-',
            'for_when': booking,
        }

    def normalize_lesson(o):
        # Build a short context: first item product name (+count if multiple)
        items = list(getattr(o, 'items', []).all()) if hasattr(o, 'items') else []
        if items:
            first_name = getattr(getattr(items[0], 'product', None), 'name', None) or 'Lesson'
            ctx = first_name if len(items) == 1 else f"{first_name} (+{len(items)-1})"
        else:
            ctx = 'Lesson Order'
        # Determine booking window from term on first item
        term = getattr(items[0], 'term', None) if items else None
        start = getattr(term, 'start_date', None)
        end = getattr(term, 'end_date', None)
        return {
            'id': o.id,
            'created': o.created,
            'user_full': o.user.get_full_name() or o.user.email,
            'user_email': o.user.email,
            'amount': o.amount,
            'paid': o.paid,
            'txId': o.txId,
            'payment_status': o.payment_status,
            'type': 'Public Lesson',
            'category': 'lessons',
            'context': ctx,
            'for_when': (f"{start} → {end}" if start and end else None),
        }

    def normalize_school(o):
        school_name = getattr(getattr(o, 'school', None), 'name', None)
        items = list(getattr(o, 'items', []).all()) if hasattr(o, 'items') else []
        term = getattr(items[0], 'term', None) if items else None
        start = getattr(term, 'start_date', None)
        end = getattr(term, 'end_date', None)
        return {
            'id': o.id,
            'created': o.created,
            'user_full': o.user.get_full_name() or o.user.email,
            'user_email': o.user.email,
            'amount': o.amount,
            'paid': o.paid,
            'txId': o.txId,
            'payment_status': o.payment_status,
            'type': 'School Lesson',
            'category': 'schools',
            'context': school_name or 'School Order',
            'for_when': (f"{start} → {end}" if start and end else None),
        }

    combined = [
        *(normalize_swim(o) for o in swims),
        *(normalize_lesson(o) for o in lessons),
        *(normalize_school(o) for o in schools),
    ]

    # Filters in Python across sources
    def match_status(item):
        if status == 'paid':
            return item['paid'] is True
        if status == 'unpaid':
            return item['paid'] is False
        return True

    def match_dates(item):
        try:
            ok = True
            if date_from:
                ok = ok and (item['created'].date().isoformat() >= date_from)
            if date_to:
                ok = ok and (item['created'].date().isoformat() <= date_to)
            return ok
        except Exception:
            return True

    def match_query(item):
        if not q:
            return True
        s = ' '.join([
            str(item.get('txId') or ''),
            str(item.get('payment_status') or ''),
            str(item.get('user_full') or ''),
            str(item.get('user_email') or ''),
            str(item.get('context') or ''),
            str(item.get('type') or ''),
        ]).lower()
        return q.lower() in s

    def match_category(item):
        if not category:
            return True
        if category == 'lessons':
            return item.get('category') in ('lessons', 'schools')
        return item.get('category') == category

    filtered = [i for i in combined if match_status(i) and match_dates(i) and match_query(i) and match_category(i)]
    filtered.sort(key=lambda x: x['created'], reverse=True)

    paginator = Paginator(filtered, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'q': q,
        'status': status,
        'category': category,
        'date_from': date_from,
        'date_to': date_to,
        'order_stats': order_stats,
    }
    return render(request, 'dashboard/orders_history.html', context)


@login_required
@user_passes_test(is_staff)
def bookings_overview(request):
    """Show bookings for Public Swims and Lesson Enrollments, with responsive tables and tabs."""
    category = request.GET.get('category', '').strip()  # "swims" | "lessons" | ""
    try:
        if not category and not (request.user.is_superuser or is_Manager(request.user)):
            category = 'swims'
    except Exception:
        pass
    # Public Swim bookings (have a concrete booking date)
    swim_bookings = (
        SwimOrder.objects.select_related('user', 'product')
        .filter(booking__isnull=False)
        .order_by('-booking', '-created')
    )
    sw_page_num = request.GET.get('sw_page')
    sw_paginator = Paginator(swim_bookings, 25)
    sw_page_obj = sw_paginator.get_page(sw_page_num)

    # Lesson enrollments (public)
    lesson_enrollments = (
        LessonEnrollment.objects.select_related('lesson', 'swimling', 'term')
        .order_by('-created')
    )
    le_page_num = request.GET.get('le_page')
    le_paginator = Paginator(lesson_enrollments, 25)
    le_page_obj = le_paginator.get_page(le_page_num)

    # School enrollments
    try:
        from schools_bookings.models import ScoEnrollment
        school_enrollments = (
            ScoEnrollment.objects.select_related('lesson', 'swimling', 'term', 'order')
            .order_by('-created')
        )
        sco_page_num = request.GET.get('sco_page')
        sco_paginator = Paginator(school_enrollments, 25)
        sco_page_obj = sco_paginator.get_page(sco_page_num)
    except Exception:
        sco_page_obj = None

    context = {
        'sw_page_obj': sw_page_obj,
        'le_page_obj': le_page_obj,
        'sco_page_obj': sco_page_obj,
        'category': category,
    }
    return render(request, 'dashboard/bookings.html', context)


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
