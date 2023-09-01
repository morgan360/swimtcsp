from datetime import date
from lessons_bookings.models import Term


def get_current_term():
    today = date.today()
    current_term = Term.objects.filter(start_date__lte=today, end_date__gte=today).first()
    return current_term


def get_previous_term():
    current_term = get_current_term()
    if current_term:
        return Term.objects.filter(id=current_term.id - 1).first()
    return none


def get_next_term():
    current_term = get_current_term()
    if current_term:
        return Term.objects.filter(id=current_term.id + 1).first()
    return none
