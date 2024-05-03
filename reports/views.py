from django.shortcuts import render
import datetime
from lessons_bookings.models import Term, LessonEnrollment
from schools_bookings.models import ScoTerm
from schools.models import ScoSchool
from .forms import ClassListForm
from django.http import HttpResponse
from lessons.models import Product, Category
from users.views import Swimling
from django.shortcuts import get_object_or_404

today = datetime.date.today()


def class_print(request):
    lesson_id = request.POST.get('lesson')
    current_term_id = Term.get_current_term_id()

    if current_term_id and lesson_id:
        swimlings = Swimling.objects.filter(
            lessonenrollment__lesson__id=lesson_id,
            lessonenrollment__term=current_term_id
        )
        product = get_object_or_404(Product, id=lesson_id)  # Retrieve the Lesson object
    else:
        swimlings = Swimling.objects.none()
        lesson = None

    return render(request, 'reports/printable_swimlings_list.html', {
        'swimlings': swimlings,
        'product': product  # Pass the Lesson object to the template
    })


# for htmx
def update_lessons(request):
    category_id = request.GET.get('category')
    day = request.GET.get('day')
    if category_id and day:
        lessons = Product.objects.filter(category_id=category_id, day_of_week=day)
    else:
        lessons = Product.objects.none()

    return render(request, 'reports/partials/lesson_options.html', {'lessons': lessons})


# for htmx
def update_days(request):
    category_id = request.GET.get('category')
    if category_id:
        # Get unique day_of_week choices for products in this category
        days = Product.objects.filter(category__id=category_id).values_list('day_of_week', flat=True).distinct()

    else:
        days = []

    # Convert days to the format expected by the template (value, display)
    day_choices = [(day, dict(Product.DAY_CHOICES)[day]) for day in days]

    return render(request, 'reports/partials/day_options.html', {'days': day_choices, "is_htmx": True})


def class_list_view(request):
    form = ClassListForm(request.GET or None)

    categories = Category.objects.all()

    # Empty initial sets for day choices and lessons
    day_choices = [choice for choice in Product.DAY_CHOICES]
    lessons = Product.objects.none()  # No lessons initially

    return render(request, 'reports/class_list.html', {
        'form': form,
        'categories': categories,
        'day_choices': day_choices,
        'lessons': lessons,
    })


def term_information(request):
    # Fetch unique School objects referred in ScoTerm
    unique_schools = ScoSchool.objects.filter(
        id__in=ScoTerm.objects.values_list('school_id', flat=True).distinct()
    ).order_by('name')

    schools_info = []
    for school in unique_schools:
        current_term = ScoTerm.get_current_term_for_school(school.id)
        if current_term:
            schools_info.append({
                'name': school.name,
                'current_term_id': current_term.id,  # Assuming you still want the ID
                'start_date': current_term.start_date,
                'end_date': current_term.end_date,
            })
        else:
            # Handle the case where there is no current term
            schools_info.append({
                'name': school.sco_name,
                'current_term_id': None,
                'start_date': None,
                'end_date': None,
            })
    # term_data = get_term_info()
    # test=term_data['next_phase']

    return render(request, 'reports/term_information.html', {
        'today': today,
        # 'current_term': current_term_string,
        # 'previous_term': previous_term_string,
        # 'next_term': next_term_string,
        # 'current_phase': current_phase,
        # 'next_phase': next_phase,
        'schools_info': schools_info,
    })
