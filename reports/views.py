from django.shortcuts import render
import datetime
from lessons_bookings.models import Term, LessonEnrollment
from .forms import ClassListForm
from django.http import HttpResponse
from lessons.models import Product, Category
from users.views import Swimling
from django.shortcuts import get_object_or_404


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


# GET ALL DATE VALUES FOR TERMS
def show_todays_date(request):
    current_term_id = Term.get_current_term_id()  # Get the ID of the current term

    if current_term_id is not None:
        try:
            current_term = Term.objects.get(id=current_term_id)
            current_term_string = current_term.concatenated_term()
            current_phase = current_term.determine_phase()

            # Fetch the previous and next term if they exist
            try:
                previous_term = Term.objects.get(id=current_term_id - 1)
                previous_term_string = previous_term.concatenated_term()
            except Term.DoesNotExist:
                previous_term_string = "No previous term"

            try:
                next_term = Term.objects.get(id=current_term_id + 1)
                next_term_string = next_term.concatenated_term()
            except Term.DoesNotExist:
                next_term_string = "No next term"
        except Term.DoesNotExist:
            current_term_string = "No current term"
            current_phase = "No current phase"
            previous_term_string = "No previous term"
            next_term_string = "No next term"
    else:
        current_term_string = "No current term"
        current_phase = "No current phase"
        previous_term_string = "No previous term"
        next_term_string = "No next term"

    today = datetime.date.today()

    return render(request, 'reports/todays_date.html', {
        'today': today,
        'current_term': current_term_string,
        'previous_term': previous_term_string,
        'next_term': next_term_string,
        'current_phase': current_phase,
    })
