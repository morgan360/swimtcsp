from datetime import date
from lessons_bookings.models import Term


def get_current_term():
    today = date.today()
    current_term = Term.objects.filter(start__lte=today, end__gte=today).first()
    return current_term
