from datetime import datetime
from typing import Dict

from django.http import HttpRequest
from django.utils import timezone
from django.conf import settings
from datetime import datetime
from typing import Dict
from django.http import HttpRequest
from lessons_bookings.models import Term
from schools.models import ScoSchool
from schools_bookings.models import ScoTerm
from utils.terms_utils import get_term_context_data
from utils.constants import PHASE_DETAILS

def get_term_info(request: HttpRequest) -> Dict[str, str]:
    data = get_term_context_data()

    current_term = data['current_term']
    next_term = data['next_term']
    previous_term = data['previous_term']
    today = data['today']

    def fmt(d):
        return d.strftime('%d %b %Y') if d else None

    start_date = fmt(current_term.start_date) if current_term else None
    end_date = fmt(current_term.end_date) if current_term else None
    rebooking_date = current_term.rebooking_date if current_term else None
    booking_date = current_term.booking_date if current_term else None

    rebooking_date_fmt = fmt(rebooking_date)
    booking_date_fmt = fmt(booking_date)

    term_string = current_term.concatenated_term() if current_term else "No current term"
    previous_term_string = previous_term.concatenated_term() if previous_term else "Previous term not found"
    next_term_string = next_term.concatenated_term() if next_term else "Next term not found"

    # 🧠 Determine active modes
    active_modes = []

    if current_term:
        if today < rebooking_date:
            active_modes = ['BK']
        elif rebooking_date <= today < booking_date:
            active_modes = ['BK', 'RB']
        elif booking_date <= today <= current_term.end_date:
            active_modes = ['BN']

    # 📌 Choose dominant phase for backward compatibility (e.g., RB takes priority over BK)
    current_phase_id = (
        'BN' if 'BN' in active_modes else
        'RB' if 'RB' in active_modes else
        'BK' if 'BK' in active_modes else
        None
    )
    # Add these after computing active_modes and current_phase_id
    current_phase_label = PHASE_DETAILS.get(current_phase_id, {}).get('label', 'Unknown')
    current_phase_end = (
        booking_date_fmt if current_phase_id in ['BK', 'RB'] else end_date
    )

    next_phase_id = None
    if current_phase_id == 'BK':
        next_phase_id = 'RB'
    elif current_phase_id == 'RB':
        next_phase_id = 'BN'

    next_phase_label = PHASE_DETAILS.get(next_phase_id, {}).get('label', '')
    next_phase_start = (
        rebooking_date_fmt if next_phase_id == 'RB'
        else booking_date_fmt if next_phase_id == 'BN'
        else None
    )

    # Use meta to build display values
    banners = []
    for mode in active_modes:
        meta = PHASE_DETAILS.get(mode, {})
        message = meta.get('description', '').format(
            rebooking_date=rebooking_date_fmt,
            booking_date=booking_date_fmt,
            end_date=end_date
        )
        banners.append({
            'id': mode,
            'label': meta.get('label', 'Unknown'),
            'message': message,
            'bulma_class': meta.get('bulma_class', 'is-light'),
        })

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
        'rebooking_date': rebooking_date_fmt,
        'booking_date': booking_date_fmt,
        'current_phase_id': current_phase_id,
        'active_modes': active_modes,
        'banners': banners,
        'next_term_start': fmt(next_term.start_date) if next_term else None,
        'next_term_end': fmt(next_term.end_date) if next_term else None,
        'phase_summary': {
            'current': {
                'id': current_phase_id,
                'label': current_phase_label,
                'until': current_phase_end
            },
            'next': {
                'id': next_phase_id,
                'label': next_phase_label,
                'starts': next_phase_start
            }
        }
    }

def footer_message(request):
    return {
        'FOOTER_MESSAGE': settings.FOOTER_MESSAGE,
        'VERSION': settings.VERSION,
    }


def term_status_for_active_schools(request):
    today = timezone.now().date()
    terms = ScoTerm.objects.filter(
        school_id__in=ScoTerm.objects.values_list('school_id', flat=True).distinct()
    ).select_related('school')

    school_status = {}

    for term in terms:
        school_id = term.school_id

        if term.start_date <= today <= term.end_date:
            # Active school term
            school_status[school_id] = {
                'school_name': term.school.name,
                'term_status': 'active',
                'term_start_date': term.start_date,
                'term_end_date': term.end_date,
                'term_id': term.id,
                'is_active': term.is_active,
            }
        else:
            future_terms = ScoTerm.objects.filter(
                school_id=school_id, start_date__gt=today
            ).order_by('start_date')
            if future_terms.exists():
                next_term = future_terms.first()
                school_status[school_id] = {
                    'school_name': next_term.school.name,
                    'term_status': 'planned',
                    'term_start_date': next_term.start_date,
                    'term_end_date': next_term.end_date,
                    'term_id': next_term.id,
                    'is_active': next_term.is_active,
                }
            elif school_id not in school_status:
                school_status[school_id] = {
                    'school_name': term.school.name,
                    'term_status': 'not planned',
                    'term_start_date': None,
                    'term_end_date': None,
                    'term_id': None,
                    'is_active': False,
                }

    return {'school_term_status': school_status}


def get_latest_active_school_term(sco_role_number):
    today = timezone.now().date()
    school = ScoSchool.objects.filter(sco_role_num=sco_role_number).first()
    if not school:
        return None
    return ScoTerm.objects.filter(
        school=school,
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).order_by('-start_date').first()