from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Q
from datetime import date

from lessons_bookings.models import Term, LessonEnrollment
from lessons.models import Product, Category
from schools_bookings.models import ScoTerm
from schools.models import ScoSchool
from users.views import Swimling
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
    length = int(request.GET.get('length', -1))  # Show all records if -1
    search_value = request.GET.get('search[value]', '')
    order_column = int(request.GET.get('order[0][column]', 0))
    order_dir = request.GET.get('order[0][dir]', 'asc')
    term_filter = request.GET.get('term_filter', 'current')

    # Resolve term
    term_lookup = {
        'current': Term.get_current_term,
        'previous': Term.get_previous_term,
        'next': Term.get_next_term,
    }
    term = term_lookup.get(term_filter, Term.get_current_term)()

    # Base queryset: all products (lessons), annotate enrollments for the term
    base_queryset = Product.objects.all().annotate(
        current_enrollments=Count('enrollments', filter=Q(enrollments__term=term))
    ).select_related('category')

    records_total = base_queryset.count()

    # Apply search filter
    if search_value:
        base_queryset = base_queryset.filter(
            Q(name__icontains=search_value) |
            Q(category__name__icontains=search_value) |
            Q(instructor__icontains=search_value)
        )

    records_filtered = base_queryset.count()
    all_products = list(base_queryset)

    # Ordering
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

    # Summary data
    total_enrollments = sum(p.current_enrollments for p in all_products)
    total_capacity = sum(p.num_places or 0 for p in all_products)
    utilization = (total_enrollments / total_capacity * 100) if total_capacity > 0 else 0

    summary = {
        'total_programs': len(all_products),
        'total_enrollments': total_enrollments,
        'total_capacity': total_capacity,
        'overall_utilization': round(utilization, 1)
    }

    # Build DataTable rows
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

    return JsonResponse({
        'draw': draw,
        'recordsTotal': records_total,
        'recordsFiltered': records_filtered,
        'data': data,
        'summary': summary,
    })


def class_print(request):
    lesson_id = request.POST.get('lesson')
    current_term_id = Term.get_current_term_id()

    swimlings = Swimling.objects.filter(
        lessonenrollment__lesson__id=lesson_id,
        lessonenrollment__term=current_term_id
    ) if current_term_id and lesson_id else Swimling.objects.none()

    product = get_object_or_404(Product, id=lesson_id) if lesson_id else None

    return render(request, 'reports/printable_swimlings_list.html', {
        'swimlings': swimlings,
        'product': product
    })


def update_lessons(request):
    category_id = request.GET.get('category')
    day = request.GET.get('day')
    lessons = Product.objects.filter(category_id=category_id, day_of_week=day) if category_id and day else Product.objects.none()
    return render(request, 'reports/partials/lesson_options.html', {'lessons': lessons})


def update_days(request):
    category_id = request.GET.get('category')
    days = Product.objects.filter(category_id=category_id).values_list('day_of_week', flat=True).distinct() if category_id else []
    day_choices = [(d, dict(Product.DAY_CHOICES)[d]) for d in days]
    return render(request, 'reports/partials/day_options.html', {'days': day_choices, 'is_htmx': True})


def class_list_view(request):
    form = ClassListForm(request.GET or None)
    categories = Category.objects.all()
    day_choices = list(Product.DAY_CHOICES)
    lessons = Product.objects.none()
    return render(request, 'reports/class_list.html', {
        'form': form,
        'categories': categories,
        'day_choices': day_choices,
        'lessons': lessons,
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
