from lessons.models import Product
from lessons_bookings.models import Term
from django.utils import timezone

def get_upcoming_terms():
    today = timezone.now().date()
    return Term.objects.filter(end_date__gte=today).order_by("start_date")

def get_active_lessons():
    return Product.objects.filter(active=True).order_by("day_of_week", "start_time")

def format_lesson_list(lessons):
    return "\n".join([
        f"- **{lesson.category.name}**: {lesson.get_day_of_week_display()} {lesson.start_time.strftime('%H:%M')}–{lesson.end_time.strftime('%H:%M')} ({lesson.num_places} places)"
        for lesson in lessons
    ])
