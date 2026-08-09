from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.db.models import Count, Q
from datetime import date
from django.utils import timezone

from lessons_bookings.models import Term, LessonEnrollment, LessonAssignment
from lessons.models import Product, Category
from instructors.models import InstructorAssignment
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
        'name', 'category__name', 'day_of_week', 'instructor',
        'current_enrollments', 'num_places', None, None
    ]
    if 0 <= order_column < len(order_columns) and order_columns[order_column]:
        order_field = order_columns[order_column]
        if order_dir == 'desc':
            order_field = '-' + order_field
        base_queryset = base_queryset.order_by(order_field)

    paginated_queryset = base_queryset if length == -1 else base_queryset[start:start + length]
    paginated_list = list(paginated_queryset)

    total_enrollments = sum(p.current_enrollments for p in all_products)
    total_capacity = sum(p.num_places or 0 for p in all_products)
    utilization = (total_enrollments / total_capacity * 100) if total_capacity > 0 else 0

    summary = {
        'total_programs': len(all_products),
        'total_enrollments': total_enrollments,
        'total_capacity': total_capacity,
        'overall_utilization': round(utilization, 1)
    }

    def format_instructor_name(user):
        if not user:
            return 'TBA'
        first = (getattr(user, 'first_name', '') or '').strip()
        last = (getattr(user, 'last_name', '') or '').strip()
        full = f"{first} {last}".strip()
        if full:
            return full
        email = getattr(user, 'email', '') or ''
        if email:
            return email
        username = getattr(user, 'get_username', None)
        if callable(username):
            try:
                return username() or 'TBA'
            except Exception:
                pass
        return str(user) if user else 'TBA'

    instructor_map = {}
    fallback_instructor_map = {}
    if term and paginated_list:
        product_ids = [p.id for p in paginated_list if getattr(p, 'id', None)]
        if product_ids:
            assigned = (
                InstructorAssignment.objects
                .select_related('instructor')
                .filter(term=term, lesson_id__in=product_ids)
            )
            instructor_map = {a.lesson_id: a.instructor for a in assigned}

            lesson_assignments = (
                LessonAssignment.objects
                .select_related('instructor')
                .filter(term=term, lessons__id__in=product_ids)
                .prefetch_related('lessons')
            )
            for assignment in lesson_assignments:
                instructor = assignment.instructor
                for lesson in assignment.lessons.all():
                    lesson_id = getattr(lesson, 'id', None)
                    if lesson_id in product_ids and lesson_id not in instructor_map and lesson_id not in fallback_instructor_map:
                        fallback_instructor_map[lesson_id] = instructor

    data = []
    for p in paginated_list:
        day_label = dict(Product.DAY_CHOICES).get(p.day_of_week, 'Not scheduled') if p.day_of_week is not None else 'Not scheduled'
        schedule_parts = []
        if p.day_of_week is not None:
            schedule_parts.append(day_label)
        if p.start_time:
            schedule_parts.append(p.start_time.strftime('%H:%M'))
        if p.end_time:
            schedule_parts.append(f"- {p.end_time.strftime('%H:%M')}")
        schedule = ' '.join(schedule_parts).strip() or 'Not scheduled'

        cap = p.num_places or 0
        enr = p.current_enrollments or 0
        util = (enr / cap * 100) if cap > 0 else 0

        data.append({
            'name': p.name,
            'category': p.category.name if p.category else 'N/A',
            'instructor': format_instructor_name(
                instructor_map.get(p.id) or
                fallback_instructor_map.get(p.id) or
                getattr(p, 'instructor', None)
            ),
            'day': day_label,
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


# The pool's term length, and the number of tick columns on a printed sheet.
TERM_WEEKS = 15


def class_print(request):
    """Print the attendance sheet for a single lesson, or for every lesson at a slot.

    The sheet is ticked by hand, so it carries a fixed fifteen week columns — the
    pool's term length — rather than a column per session actually scheduled.
    """
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
            'term_label': term_choice.title() + " Term",
            'weeks': range(1, TERM_WEEKS + 1),
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
            'weeks': range(1, TERM_WEEKS + 1),
        })

    # Fallback: nothing matched; render a simple empty state
    return render(request, 'reports/printable_swimlings_list.html', {
        'swimlings': [],
        'product': None,
        'term_label': term_choice.title() + " Term",
        'weeks': range(1, TERM_WEEKS + 1),
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


def _get_school_terms_for_filter(filter_key, school_id=None):
    today = timezone.localdate()
    base_qs = ScoTerm.objects.all()
    if school_id:
        base_qs = base_qs.filter(school_id=school_id)

    if filter_key == 'previous':
        return list(base_qs.filter(end_date__lt=today).order_by('-end_date')[:1])
    if filter_key == 'next':
        return list(base_qs.filter(start_date__gt=today).order_by('start_date')[:1])

    qs = base_qs.filter(start_date__lte=today, end_date__gte=today).order_by('start_date')
    if qs.exists():
        return list(qs)
    qs = base_qs.filter(is_active=True).order_by('-start_date')
    if qs.exists():
        return list(qs[:1])
    return list(base_qs.order_by('-start_date')[:1])


def _school_term_label(terms, fallback):
    if not terms:
        return fallback
    term = terms[0]
    school_name = getattr(getattr(term, 'school', None), 'name', 'All Schools')
    start = getattr(term, 'start_date', None)
    end = getattr(term, 'end_date', None)
    if start and end:
        return f"{school_name} • {start:%d %b %Y} – {end:%d %b %Y}"
    return f"{school_name} • Term {term.id}"


def _build_school_enrollment_rows(terms, school_id=None, day=None):
    term_ids = [t.id for t in terms]
    if school_id:
        try:
            school_ids = [int(school_id)]
        except (TypeError, ValueError):
            school_ids = [t.school_id for t in terms if getattr(t, 'school_id', None)]
    else:
        school_ids = [t.school_id for t in terms if getattr(t, 'school_id', None)]

    lessons_qs = ScoLessons.objects.select_related('category', 'school')
    if school_ids:
        lessons_qs = lessons_qs.filter(school_id__in=school_ids)
    lessons_qs = lessons_qs.filter(active=True)
    if day not in (None, '', 'null'):
        try:
            lessons_qs = lessons_qs.filter(day_of_week=int(day))
        except (TypeError, ValueError):
            lessons_qs = lessons_qs.none()

    lessons = list(lessons_qs)
    if not lessons:
        return [], {
            "total_programs": 0,
            "total_enrollments": 0,
            "total_capacity": 0,
            "utilization": 0,
        }

    enrollment_map = {}
    if term_ids:
        enrollment_map = {
            row['lesson_id']: row['total']
            for row in (
                ScoEnrollment.objects
                .filter(term_id__in=term_ids, lesson_id__in=[lesson.id for lesson in lessons])
                .values('lesson_id')
                .annotate(total=Count('id'))
            )
        }

    rows = []
    total_capacity = 0
    total_enrollments = 0

    for lesson in lessons:
        capacity = lesson.num_places or 0
        enrolled = enrollment_map.get(lesson.id, 0)
        spaces_left = capacity - enrolled if capacity else 0
        spaces_left = spaces_left if spaces_left >= 0 else 0

        schedule_parts = []
        try:
            schedule_parts.append(lesson.get_day_of_week_display())
        except Exception:
            pass
        if getattr(lesson, 'start_time', None):
            schedule_parts.append(lesson.start_time.strftime('%H:%M'))
        if getattr(lesson, 'end_time', None):
            schedule_parts.append(f"- {lesson.end_time.strftime('%H:%M')}")
        schedule = ' '.join(schedule_parts).strip()

        rows.append({
            'name': lesson.name,
            'category': lesson.category.name if lesson.category else '—',
            'school': getattr(lesson.school, 'name', 'Unassigned'),
            'schedule': schedule,
            'enrollments': enrolled,
            'capacity': capacity,
            'spaces_left': spaces_left,
        })

        total_capacity += capacity
        total_enrollments += enrolled

    rows.sort(key=lambda r: (r['enrollments'], r['capacity']), reverse=True)

    summary = {
        "total_programs": len(lessons),
        "total_enrollments": total_enrollments,
        "total_capacity": total_capacity,
        "utilization": round((total_enrollments / total_capacity) * 100, 1) if total_capacity else 0,
    }
    return rows, summary


def school_enrollment_report(request):
    schools = ScoSchool.objects.filter(school_lessons__isnull=False).distinct().order_by('name')
    day_choices = sorted({
        (lesson.day_of_week, lesson.get_day_of_week_display())
        for lesson in ScoLessons.objects.filter(active=True)
    })

    term_options_data = [
        ('current', "Active School Terms"),
        ('next', "Upcoming School Term"),
        ('previous', "Most Recent School Term"),
    ]
    options = []
    default_key = None
    for key, fallback in term_options_data:
        terms = _get_school_terms_for_filter(key, None)
        label = _school_term_label(terms, fallback)
        has_terms = bool(terms)
        options.append({
            'key': key,
            'label': label,
            'disabled': not has_terms,
        })
        if not default_key and has_terms:
            default_key = key
    if default_key is None:
        default_key = 'current'

    context = {
        'term_options': options,
        'default_term': default_key,
        'schools': schools,
        'default_school': '',
        'day_choices': day_choices,
        'default_day': '',
    }
    return render(request, 'reports/school_enrollment_report.html', context)


def school_enrollment_report_data(request):
    term_filter = request.GET.get('term_filter', 'current')
    school_id = request.GET.get('school_id', '').strip()
    if not school_id:
        school_id = None
    else:
        try:
            school_id = int(school_id)
        except (TypeError, ValueError):
            school_id = None
    filters = ['previous', 'current', 'next']
    term_sets = {key: _get_school_terms_for_filter(key, school_id) for key in filters}

    selected_terms = term_sets.get(term_filter, [])
    data, selected_summary = _build_school_enrollment_rows(selected_terms, school_id)

    summary = {}
    for key, terms in term_sets.items():
        _, sum_stats = _build_school_enrollment_rows(terms, school_id)
        summary[key] = sum_stats

    return JsonResponse({
        'data': data,
        'summary': summary,
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
