from datetime import datetime
from django.utils import formats
from lessons_bookings.models import Term
from schools_bookings.models import ScoTerm
from django.http import HttpRequest
from typing import Dict
from django.utils import timezone
from django.utils.formats import date_format
from utils.terms_utils import get_term_context_data

from datetime import datetime
from django.utils import formats
from lessons_bookings.models import Term
from schools_bookings.models import ScoTerm
from django.http import HttpRequest
from typing import Dict
from django.utils import timezone
from django.utils.formats import date_format
from utils.terms_utils import get_term_context_data

def get_term_info(request: HttpRequest) -> Dict[str, str]:
    data = get_term_context_data()

    current_term = data['current_term']
    next_term = data['next_term']
    previous_term = data['previous_term']
    phase_id = data['current_phase_id']
    today = data['today']

    # 📌 determine booking_term for display
    if current_term and current_term.rebooking_date and today >= current_term.rebooking_date:
        booking_term = next_term
    else:
        booking_term = current_term

    def fmt(d):
        return d.strftime('%d %b %Y') if d else None

    start_date = fmt(booking_term.start_date) if booking_term else None
    end_date = fmt(booking_term.end_date) if booking_term else None
    rebooking_date = fmt(current_term.rebooking_date) if current_term else None
    booking_date = fmt(current_term.booking_date) if current_term else None

    term_string = booking_term.concatenated_term() if booking_term else "No current term"
    previous_term_string = previous_term.concatenated_term() if previous_term else "Previous term not found"
    next_term_string = next_term.concatenated_term() if next_term else "Next term not found"

    phase_string = "Phase not found"
    next_phase_string = "Next phase not found"
    next_phase_id = None

    if phase_id == 'BK':
        next_phase_id = 'RB'
        phase_string = f'Booking for This Term: Closes ~ {rebooking_date}'
        next_phase_string = f'ReBooking for Next Term: Starts ~ {rebooking_date}'
    elif phase_id == 'RB':
        next_phase_id = 'BN'
        phase_string = f'ReBooking for Next Term until {booking_date}'
        next_phase_string = f'Booking for Next Term: starts {booking_date}'
    elif phase_id == 'BN':
        phase_string = f'Booking for Next Term until {end_date}'

    print("📌 [DEBUG get_term_info]")
    print(f"  🕒 Today: {today}")
    print(f"  📘 Current Term: {current_term} (ID: {getattr(current_term, 'id', None)})")
    print(f"  📗 Next Term: {next_term} (ID: {getattr(next_term, 'id', None)})")
    print(f"  📙 Booking Term: {booking_term} (ID: {getattr(booking_term, 'id', None)})")
    print(f"  ⏳ Phase: {phase_id}")
    print(f"  🗓️  Start: {start_date}, End: {end_date}")
    print(f"  🔁 Rebooking: {rebooking_date}, Booking: {booking_date}")

    return {
        'today': today,
        'current_term_id': current_term.id if current_term else None,
        'current_term': term_string,
        'next_term_id': next_term.id if next_term else None,
        'next_term': next_term_string,
        'previous_term_id': previous_term.id if previous_term else None,
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
