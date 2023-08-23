from datetime import date
from lessons_bookings.models import Term


def get_current_term():
    today = date.today()
    current_term = Term.objects.filter(start_date__lte=today, end_date__gte=today).first()
    return current_term
