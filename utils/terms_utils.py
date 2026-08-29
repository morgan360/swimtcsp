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
    today = timezone.now().date()
    current_term = get_current_term()

    future_terms = Term.objects.filter(start_date__gt=today).order_by('start_date')
    if current_term:
        return future_terms.filter(start_date__gt=current_term.end_date).first() or future_terms.first()

    return future_terms.first()

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


def acting_as_staff(request):
    """Is the person driving this request a member of staff?

    True for a logged-in staff member or superuser, and also inside a
    django-hijack session: impersonating a guardian is how staff book on that
    guardian's behalf, and a hijacked request carries the guardian's own
    (non-staff) user. HIJACK_PERMISSION_CHECK restricts hijacking to staff and
    superusers, so the presence of a hijack history is proof of a staff hijacker.
    """
    if request is None:
        return False

    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated and (user.is_staff or user.is_superuser):
        return True

    session = getattr(request, 'session', None)
    return bool(session and session.get('hijack_history'))


def public_booking_paused(request=None, phase=None):
    """Is public lesson booking currently inside the pause window?

    The pause sits between a term's pause_date and its booking_date. It closes
    lesson booking to the public only — staff keep booking swimlings into
    classes throughout, which is the whole point of the window.

    Pass `phase` when the caller has already resolved the phase, to save the
    term lookup.
    """
    if phase is None:
        phase = get_term_context_data()['current_phase_id']
    return phase == 'PA' and not acting_as_staff(request)


def booking_pause_notice(term=None):
    """The message shown to the public when they hit the pause."""
    if term is None:
        term = get_current_term()
    reopens = term.booking_date if term else None
    if reopens:
        return (
            f"Lesson booking is paused while classes are finalised. "
            f"It reopens on {reopens:%d %b %Y}."
        )
    return "Lesson booking is paused while classes are finalised."
