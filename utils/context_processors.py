from datetime import datetime
from django.utils import formats
from lessons_bookings.models import Term
from schools_bookings.models import ScoTerm
from django.http import HttpRequest
from typing import Dict
from django.utils import timezone
from django.utils.formats import date_format


def get_term_info(request: HttpRequest) -> Dict[str, str]:
    """
    Context processor to retrieve the current term, its current phase, and the next phase.

    Args:
    - request: HttpRequest object.

    Returns:
    - Dictionary with keys 'current_term', 'current_phase', and 'next_phase' associated to the current term's string
      representation, its current phase, and the next phase, or messages indicating no current term or phases not found, respectively.
    """
    today = timezone.now().date()
    # Initialize all variables to ensure they have default values
    current_term_id = None
    next_term_id = None
    previous_term_id = None
    start_date = None
    end_date = None
    rebooking_date = None
    booking_date = None
    phase_id = None
    next_phase_id = None
    term_string = "No current term"
    phase_string = "Phase not found"
    next_phase_string = "Next phase not found"
    previous_term_string = "Previous term not found"
    next_term_string = "Next term not found"

    try:
        current_term_id = Term.get_current_term_id()
        if current_term_id is not None:
            term = Term.objects.get(id=current_term_id)
            term_string = term.concatenated_term()
            start_date = term.start_date.strftime('%d %b %Y')
            end_date = term.end_date.strftime('%d %b %Y')
            rebooking_date = term.rebooking_date.strftime('%d %b %Y')
            booking_date = term.booking_date.strftime('%d %b %Y')

            # Checking for previous term
            previous_term = Term.objects.filter(end_date__lt=term.start_date).order_by('-end_date').first()
            if previous_term:
                previous_term_id = previous_term.id
                previous_term_string = previous_term.concatenated_term()
            else:
                previous_term_id = None
                previous_term_string = "Previous term not found"

            # Checking for next term
            next_term = Term.objects.filter(start_date__gt=term.end_date).order_by('start_date').first()
            if next_term:
                next_term_id = next_term.id
                next_term_string = next_term.concatenated_term()
            else:
                next_term_id = None
                next_term_string = "Next term not found"

            # Check and retrieve the current phase
            if hasattr(term, 'determine_phase'):
                phase_id = term.determine_phase()
                if phase_id == 'BK':
                    next_phase_id = 'RB'
                    phase_string = f'Booking for This Term: Closes ~ {rebooking_date}'
                    next_phase_string = f'ReBooking for Next Term: Starts ~ {rebooking_date}'
                elif phase_id == 'RB':
                    next_phase_id = 'BN'
                    phase_string = f'ReBooking for Next Term  until {booking_date}'
                    next_phase_string = f'Booking for Next Term: starts {booking_date}'
                elif phase_id == 'BN':
                    phase_string = f'Booking for Next Term until {end_date}'
            else:
                phase_string = "Phase method not available"

    except Term.DoesNotExist:
        term_string = "Term not found"

    return {
        'today': today,
        'current_term_id': current_term_id,
        'current_term': term_string,
        'next_term_id': next_term_id,
        'next_term': next_term_string,
        'previous_term_id': previous_term_id,
        'previous_term': previous_term_string,
        'start_date': start_date,
        'end_date': end_date,
        'rebooking_date': rebooking_date,
        'booking_date': booking_date,
        'current_phase_id': phase_id,
        'current_phase': phase_string,
        'next_phase_id': next_phase_id,
        'next_phase': next_phase_string,
    }


# Different Footer for each version production, local
def footer_message(request):
    from django.conf import settings
    return {'FOOTER_MESSAGE': settings.FOOTER_MESSAGE}


def term_status_for_active_schools(request):
    today = timezone.now().date()
    # Fetch all terms for schools that have at least one term
    terms = ScoTerm.objects.filter(
        school_id__in=ScoTerm.objects.values_list('school_id', flat=True).distinct()
    ).select_related('school')  # Optimized to fetch school data in the same query

    school_status = {}

    for term in terms:
        school_id = term.school_id
        # Checking if the term is currently active based on the date
        if term.start_date <= today <= term.end_date:
            school_status[school_id] = {
                'school_name': term.school.name,
                'term_status': 'active',
                'term_start_date': term.start_date,
                'term_end_date': term.end_date,
                'term_id': term.id,
                'is_active': term.is_active  # Include the active status of the term
            }
        else:
            # Check for future terms
            future_terms = ScoTerm.objects.filter(
                school_id=school_id, start_date__gt=today).order_by('start_date')
            if future_terms.exists():
                next_term = future_terms.first()
                school_status[school_id] = {
                    'school_name': next_term.school.name,
                    'term_status': 'planned',
                    'term_start_date': next_term.start_date,
                    'term_end_date': next_term.end_date,
                    'term_id': next_term.id,
                    'is_active': next_term.is_active  # Include the active status of the term
                }
            else:
                # If no future terms and not already listed as active
                if school_id not in school_status:
                    school_status[school_id] = {
                        'school_name': term.school.name,
                        'term_status': 'not planned',
                        'term_start_date': None,
                        'term_end_date': None,
                        'term_id': None,
                        'is_active': False  # Since no active or planned terms are found, set is_active to False
                    }

    return {'school_term_status': school_status}
