from datetime import date
from django.utils import timezone
from lessons_bookings.models import Term
from schools_bookings.models import ScoTerm

def get_current_term():
    today = timezone.now().date()
    current_term = Term.objects.filter(start_date__lte=today, end_date__gte=today).first()
    return current_term

def get_previous_term():
    current_term = get_current_term()
    if current_term:
        previous_term = Term.objects.filter(end_date__lt=current_term.start_date).order_by('-end_date').first()
        return previous_term
    return None

def get_next_term():
    current_term = get_current_term()
    if current_term:
        next_term = Term.objects.filter(start_date__gt=current_term.end_date).order_by('start_date').first()
        return next_term
    return None

def get_current_sco_term():
    today = timezone.now().date()
    current_sco_term = ScoTerm.objects.filter(start_date__lte=today, end_date__gte=today).first()
    return current_sco_term

def get_term_context_data():
    today = timezone.now().date()

    current_term = get_current_term()
    next_term = get_next_term()
    previous_term = get_previous_term()

    current_phase_id = None
    if current_term and hasattr(current_term, 'determine_phase'):
        current_phase_id = current_term.determine_phase()

    return {
        'today': today,
        'current_term': current_term,
        'next_term': next_term,
        'previous_term': previous_term,
        'current_phase_id': current_phase_id,
    }
