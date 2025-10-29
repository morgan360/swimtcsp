from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.db.models import Count, Q
from datetime import date

from lessons_bookings.models import Term, LessonEnrollment
from lessons.models import Product, Category
from schools_bookings.models import ScoTerm, ScoEnrollment
from schools.models import ScoSchool, ScoLessons
from users.models import Swimling
from .forms import ClassListForm


today = date.today()


def enrollment_report(request):
    """Render the enrollment report page"""
    context = {
        'current_term': Term.get_current_term(),
        'previous_term': Term.get_previous_term(),
        'next_term': Term.get_next_term(),
    }
    return render(request, 'reports/enrollment_report.html', context)


def enrollment_report_data(request):
    """AJAX endpoint for DataTables"""
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', -1))
    search_value = request.GET.get('search[value]', '')
    order_column = int(request.GET.get('order[0][column]', 0))
    order_dir = request.GET.get('order[0][dir]', 'asc')
    term_filter = request.GET.get('term_filter', 'current')

    term_lookup = {
        'current': Term.get_current_term,
        'previous': Term.get_previous_term,
        'next': Term.get_next_term,
    }
    term = term_lookup.get(term_filter, Term.get_current_term)()

    base_queryset = Product.objects.all().annotate(
        current_enrollments=Count('enrollments', filter=Q(enrollments__term=term))
    ).select_related('category')

    records_total = base_queryset.count()

    if search_value:
        base_queryset = base_queryset.filter(
            Q(name__icontains=search_value) |
            Q(category__name__icontains=search_value) |
            Q(instructor__icontains=search_value)
        )

    records_filtered = base_queryset.count()
    all_products = list(base_queryset)

    order_columns = [
        'name', 'category__name', 'instructor', 'day_of_week',
        'current_enrollments', 'num_places', None, None
    ]
    if 0 <= order_column < len(order_columns) and order_columns[order_column]:
        order_field = order_columns[order_column]
        if order_dir == 'desc':
            order_field = '-' + order_field
        base_queryset = base_queryset.order_by(order_field)

    paginated_queryset = base_queryset if length == -1 else base_queryset[start:start + length]

    total_enrollments = sum(p.current_enrollments for p in all_products)
    total_capacity = sum(p.num_places or 0 for p in all_products)
    utilization = (total_enrollments / total_capacity * 100) if total_capacity > 0 else 0

    summary = {
        'total_programs': len(all_products),
        'total_enrollments': total_enrollments,
        'total_capacity': total_capacity,
        'overall_utilization': round(utilization, 1)
    }

    data = []
    for p in paginated_queryset:
        schedule = ' '.join(filter(None, [
            dict(Product.DAY_CHOICES).get(p.day_of_week, p.day_of_week) if p.day_of_week else None,
            p.start_time.strftime('%H:%M') if p.start_time else '',
            f"- {p.end_time.strftime('%H:%M')}" if p.end_time else ''
        ])).strip() or 'Not scheduled'

        cap = p.num_places or 0
        enr = p.current_enrollments or 0
        util = (enr / cap * 100) if cap > 0 else 0

        data.append({
            'name': p.name,
            'category': p.category.name if p.category else 'N/A',
            'instructor': getattr(p, 'instructor', 'TBA') or 'TBA',
            'schedule': schedule,
            'enrollments': enr,
            'capacity': cap,
            'spaces_left': cap - enr,
            'utilization': round(util, 1),
        })

    if order_column == 6:
        data.sort(key=lambda x: x['spaces_left'], reverse=(order_dir == 'desc'))
    elif order_column == 7:
        data.sort(key=lambda x: x['utilization'], reverse=(order_dir == 'desc'))

    def calculate_summary(products):
        total_programs = len(products)
        total_enrollments = sum(p.current_enrollments for p in products)
        total_capacity = sum(p.num_places or 0 for p in products)
        utilization = (total_enrollments / total_capacity * 100) if total_capacity > 0 else 0
        return {
            "total_programs": total_programs,
            "total_enrollments": total_enrollments,
            "total_capacity": total_capacity,
            "utilization": round(utilization, 1)
        }

    # Calculate all summaries
    summary = {
        "previous": calculate_summary(
            Product.objects.annotate(
                current_enrollments=Count('enrollments', filter=Q(enrollments__term=Term.get_previous_term()))
            )
        ),
        "current": calculate_summary(
            Product.objects.annotate(
                current_enrollments=Count('enrollments', filter=Q(enrollments__term=Term.get_current_term()))
            )
        ),
        "next": calculate_summary(
            Product.objects.annotate(
                current_enrollments=Count('enrollments', filter=Q(enrollments__term=Term.get_next_term()))
            )
        ),
    }

    return JsonResponse({
        "data": data,
        "summary": summary,
    })


def class_print(request):
    """Print swimlings for either a single lesson or all lessons at a time slot."""
    lesson_id = request.GET.get('lesson')
    term_choice = request.GET.get('term', 'current')
    category_id = request.GET.get('category')
    day = request.GET.get('day')
    time_str = request.GET.get('time')

    term_lookup = {
        'current': Term.get_current_term,
        'next': Term.get_next_term,
        'previous': Term.get_previous_term,
    }
    term = term_lookup.get(term_choice, Term.get_current_term)()

    # Case 1: specific lesson provided → print one class list
    if term and lesson_id:
        swimlings = Swimling.objects.filter(
            enrollments__lesson__id=lesson_id,
            enrollments__term=term
        ).select_related('guardian').order_by('first_name', 'last_name')
        product = get_object_or_404(Product, id=lesson_id)
        return render(request, 'reports/printable_swimlings_list.html', {
            'swimlings': swimlings,
            'product': product,
            'term_label': term_choice.title() + " Term"
        })

    # Case 2: filter by term + day + time → print all lessons at that time
    products = Product.objects.none()
    if term and day and time_str:
        try:
            from datetime import time as dt_time
            hh, mm = [int(x) for x in time_str.split(':', 1)]
            products = Product.objects.filter(
                day_of_week=int(day),
                start_time=dt_time(hour=hh, minute=mm),
                active=True,
            )
            if category_id:
                products = products.filter(category_id=category_id)
            products = products.select_related('category').order_by('name')
        except Exception:
            products = Product.objects.none()

    lesson_lists = []
    for p in products:
        s = list(
            Swimling.objects
            .filter(enrollments__lesson=p, enrollments__term=term)
            .select_related('guardian')
            .order_by('first_name', 'last_name')
        )
        lesson_lists.append({'product': p, 'swimlings': s})

    if lesson_lists:
        return render(request, 'reports/printable_swimlings_list_multi.html', {
            'lesson_lists': lesson_lists,
            'term_label': term_choice.title() + " Term",
            'time_label': time_str,
        })

    # Fallback: nothing matched; render a simple empty state
    return render(request, 'reports/printable_swimlings_list.html', {
        'swimlings': [],
        'product': None,
        'term_label': term_choice.title() + " Term"
    })


def _school_filter_context(school_id=None, selected_day=None, selected_time=None):
    """Build reusable context for school class list filters."""
    context = {
        'terms': [],
        'day_choices': [],
        'time_choices': [],
        'lessons': [],
    }
    if not school_id:
        return context

    lessons = ScoLessons.objects.filter(school_id=school_id, active=True).select_related('school')

    terms = ScoTerm.objects.filter(school_id=school_id).order_by('-start_date', '-id')
    context['terms'] = terms

    day_label_map = dict(ScoLessons._meta.get_field('day_of_week').choices)
    day_values = sorted({lesson.day_of_week for lesson in lessons})
    context['day_choices'] = [(day, day_label_map.get(day, str(day))) for day in day_values]

    filtered_lessons = lessons
    if selected_day not in (None, '', 'null'):
        try:
            day_int = int(selected_day)
            filtered_lessons = filtered_lessons.filter(day_of_week=day_int)
        except (TypeError, ValueError):
            filtered_lessons = lessons.none()

    time_choices = sorted({
        lesson.start_time.strftime('%H:%M')
        for lesson in filtered_lessons
        if lesson.start_time
    })
    context['time_choices'] = time_choices

    if selected_time:
        try:
            from datetime import time as dt_time
            hh, mm = [int(x) for x in selected_time.split(':', 1)]
            filtered_lessons = filtered_lessons.filter(start_time=dt_time(hour=hh, minute=mm))
        except Exception:
            filtered_lessons = filtered_lessons.none()

    context['lessons'] = filtered_lessons.order_by('name')
    return context


def school_class_list_view(request):
    selected_school = request.GET.get('school') or ''
    selected_term = request.GET.get('term') or ''
    selected_day = request.GET.get('day') or ''
    selected_time = request.GET.get('time') or ''
    selected_lesson = request.GET.get('lesson') or ''

    schools = (
        ScoSchool.objects.filter(school_lessons__isnull=False)
        .distinct()
        .order_by('name')
    )

    filter_data = _school_filter_context(
        selected_school or None,
        selected_day or None,
        selected_time or None,
    )

    context = {
        'schools': schools,
        'selected_school': selected_school,
        'selected_term': selected_term,
        'selected_day': selected_day,
        'selected_time': selected_time,
        'selected_lesson': selected_lesson,
        **filter_data,
    }
    return render(request, 'reports/school_class_list.html', context)


def update_school_filters(request):
    """HTMX endpoint to refresh term/day/time/lesson selects when school changes."""
    school_id = request.GET.get('school') or ''
    selected_day = request.GET.get('day') or ''
    selected_time = request.GET.get('time') or ''
    selected_term = request.GET.get('term') or ''
    selected_lesson = request.GET.get('lesson') or ''

    filter_data = _school_filter_context(
        school_id or None,
        selected_day or None,
        selected_time or None,
    )

    context = {
        'selected_term': selected_term,
        'selected_day': selected_day,
        'selected_time': selected_time,
        'selected_lesson': selected_lesson,
        **filter_data,
    }
    return render(request, 'reports/partials/school_filter_controls.html', context)


def update_school_times(request):
    school_id = request.GET.get('school') or ''
    selected_day = request.GET.get('day') or ''

    times = []
    if school_id and selected_day not in ('', None, 'null'):
        try:
            day_int = int(selected_day)
            lessons = ScoLessons.objects.filter(
                school_id=school_id,
                day_of_week=day_int,
                active=True,
            )
            times = sorted({
                lesson.start_time.strftime('%H:%M')
                for lesson in lessons if lesson.start_time
            })
        except (TypeError, ValueError):
            times = []

    return render(request, 'reports/partials/school_time_options.html', {
        'times': times,
    })


def update_school_lessons(request):
    school_id = request.GET.get('school') or ''
    selected_day = request.GET.get('day') or ''
    time_str = request.GET.get('time') or ''

    lessons = ScoLessons.objects.none()
    if school_id:
        lessons = ScoLessons.objects.filter(school_id=school_id, active=True)
        if selected_day not in ('', None, 'null'):
            try:
                lessons = lessons.filter(day_of_week=int(selected_day))
            except (TypeError, ValueError):
                lessons = lessons.none()
        if time_str:
            try:
                from datetime import time as dt_time
                hh, mm = [int(x) for x in time_str.split(':', 1)]
                lessons = lessons.filter(start_time=dt_time(hour=hh, minute=mm))
            except Exception:
                lessons = lessons.none()
        lessons = lessons.order_by('name')

    return render(request, 'reports/partials/school_lesson_options.html', {
        'lessons': lessons,
    })


def school_class_print(request):
    school_id = request.GET.get('school')
    term_id = request.GET.get('term')
    selected_day = request.GET.get('day')
    time_str = request.GET.get('time')
    lesson_id = request.GET.get('lesson')

    if not school_id or not term_id:
        return HttpResponseBadRequest("School and term are required to generate a class list.")

    school = get_object_or_404(ScoSchool, pk=school_id)
    term = get_object_or_404(ScoTerm, pk=term_id, school=school)

    def unique_swimlings(enrollments_qs):
        seen = set()
        swimlings = []
        for enrollment in enrollments_qs:
            if enrollment.swimling_id not in seen:
                seen.add(enrollment.swimling_id)
                swimlings.append(enrollment.swimling)
        return swimlings

    if lesson_id:
        lesson = get_object_or_404(
            ScoLessons.objects.select_related('school'),
            pk=lesson_id,
            school=school,
        )
        enrollments = (
            ScoEnrollment.objects
            .filter(lesson=lesson, term=term)
            .select_related('swimling', 'swimling__guardian')
            .order_by('swimling__first_name', 'swimling__last_name', 'id')
        )
        swimlings = unique_swimlings(enrollments)
        return render(request, 'reports/printable_school_swimlings_list.html', {
            'swimlings': swimlings,
            'lesson': lesson,
            'school': school,
            'term': term,
        })

    lessons = ScoLessons.objects.filter(school=school, active=True)
    if selected_day not in ('', None, 'null'):
        try:
            lessons = lessons.filter(day_of_week=int(selected_day))
        except (TypeError, ValueError):
            lessons = lessons.none()
    if time_str:
        try:
            from datetime import time as dt_time
            hh, mm = [int(x) for x in time_str.split(':', 1)]
            lessons = lessons.filter(start_time=dt_time(hour=hh, minute=mm))
        except Exception:
            lessons = lessons.none()

    lesson_lists = []
    for lesson in lessons.order_by('name'):
        enrollments = (
            ScoEnrollment.objects
            .filter(lesson=lesson, term=term)
            .select_related('swimling', 'swimling__guardian')
            .order_by('swimling__first_name', 'swimling__last_name', 'id')
        )
        swimlings = unique_swimlings(enrollments)
        lesson_lists.append({'lesson': lesson, 'swimlings': swimlings})

    if lesson_lists:
        return render(request, 'reports/printable_school_swimlings_list_multi.html', {
            'lesson_lists': lesson_lists,
            'school': school,
            'term': term,
            'time_label': time_str,
        })

    return render(request, 'reports/printable_school_swimlings_list.html', {
        'swimlings': [],
        'lesson': None,
        'school': school,
        'term': term,
    })


def update_lessons(request):
    print("update_lessons:", request.GET)
    day = request.GET.get('day')
    time_str = request.GET.get('time')
    lessons = Product.objects.all()
    # Day is required to populate lessons list
    if day not in [None, '', 'null', 'undefined']:
        try:
            lessons = lessons.filter(day_of_week=int(day))
        except (TypeError, ValueError):
            lessons = Product.objects.none()
    else:
        lessons = Product.objects.none()
    # Optional time filter to narrow lessons at a specific time
    if time_str:
        try:
            from datetime import time as dt_time
            hh, mm = [int(x) for x in time_str.split(':', 1)]
            lessons = lessons.filter(start_time=dt_time(hour=hh, minute=mm))
        except Exception:
            pass
    return render(request, 'reports/partials/lesson_options.html', {'lessons': lessons})

def update_days(request):
    # Return all distinct days present in lessons (category removed)
    days = Product.objects.values_list('day_of_week', flat=True).distinct()
    day_choices = [(d, dict(Product.DAY_CHOICES)[d]) for d in days]
    return render(request, 'reports/partials/day_options.html', {'days': day_choices})

def update_times(request):
    day = request.GET.get('day')
    times = []
    if day not in [None, '', 'null', 'undefined']:
        try:
            q = Product.objects.filter(day_of_week=int(day))
            times = sorted({p.start_time.strftime('%H:%M') for p in q if p.start_time})
        except (TypeError, ValueError):
            times = []
    return render(request, 'reports/partials/time_options.html', {'times': times})


def class_list_view(request):
    form = ClassListForm(request.GET or None)
    categories = Category.objects.all()
    day_choices = list(Product.DAY_CHOICES)
    lessons = Product.objects.none()
    swimlings = []
    selected_lesson = None
    selected_term_label = None

    # Extract from GET
    lesson_id = request.GET.get('lesson')
    term_choice = request.GET.get('term', 'current')

    # If user has selected a lesson and term
    if lesson_id:
        # Map term choices
        term_lookup = {
            'current': Term.get_current_term,
            'next': Term.get_next_term,
            'previous': Term.get_previous_term,
        }
        term = term_lookup.get(term_choice, Term.get_current_term)()
        selected_term_label = term_choice.title()

        # Get swimlings for the lesson+term
        swimlings = Swimling.objects.filter(
            enrollments__lesson_id=lesson_id,
            enrollments__term=term
        ).select_related('guardian').order_by('first_name')

        selected_lesson = Product.objects.filter(id=lesson_id).first()

    return render(request, 'reports/class_list.html', {
        'form': form,
        'categories': categories,
        'day_choices': day_choices,
        'lessons': lessons,
        'swimlings': swimlings,
        'selected_lesson': selected_lesson,
        'selected_term_label': selected_term_label,
    })


def term_information(request):
    unique_schools = ScoSchool.objects.filter(
        id__in=ScoTerm.objects.values_list('school_id', flat=True).distinct()
    ).order_by('name')

    schools_info = []
    for school in unique_schools:
        current_term = ScoTerm.get_current_term_for_school(school.id)
        schools_info.append({
            'name': school.name,
            'current_term_id': current_term.id if current_term else None,
            'start_date': current_term.start_date if current_term else None,
            'end_date': current_term.end_date if current_term else None,
        })

    return render(request, 'reports/term_information.html', {
        'today': today,
        'schools_info': schools_info,
    })
