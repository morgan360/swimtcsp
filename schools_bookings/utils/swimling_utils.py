# schools_bookings/utils/swimling_utils.py

from django.utils import timezone
from schools.models import ScoSchool
from schools_bookings.models import ScoTerm, ScoEnrollment


def get_latest_active_school_term(sco_role_number):
    """
    Get the active school term for booking.
    Returns any term marked as active, regardless of dates,
    to allow advance booking for future terms.
    """
    school = ScoSchool.objects.filter(sco_role_num=sco_role_number).first()
    if not school:
        return None
    return ScoTerm.objects.filter(
        school=school,
        is_active=True
    ).order_by('-start_date').first()


def swimling_is_enrolled(swimling, term):
    return ScoEnrollment.objects.filter(swimling=swimling, term=term).exists()

