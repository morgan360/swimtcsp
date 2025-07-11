# swimling_dashboard/templatetags/custom_filters.py

from django import template
from schools_bookings.utils.swimling_utils import get_latest_active_school_term, swimling_is_enrolled

register = template.Library()

@register.filter
def get_active_school_term(swimling):
    return get_latest_active_school_term(swimling.sco_role_num)

@register.filter
def is_enrolled_in_term(swimling, term):
    return swimling_is_enrolled(swimling, term)
