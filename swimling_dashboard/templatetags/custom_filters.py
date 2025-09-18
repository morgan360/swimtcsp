from django import template
from schools_bookings.utils.swimling_utils import get_latest_active_school_term, swimling_is_enrolled
from django.utils.safestring import mark_safe



register = template.Library()

@register.filter
def get_active_school_term(swimling):
    return get_latest_active_school_term(swimling.sco_role_num)

@register.filter
def is_enrolled_in_term(swimling, term):
    return swimling_is_enrolled(swimling, term)

@register.filter
def get_next_for(next_lessons, current_lesson):
    """
    Return the next-term lesson(s) if the swimling is booked,
    regardless of whether it's the same class as the current term.
    """
    if not next_lessons:
        return None
    # Just return the first booked next-term lesson
    return next_lessons.first()

@register.filter
def get_action(actions, label):
    """
    Given a list of action dicts and a label string (e.g., "Rebook"),
    return the matching action dict (e.g., {'label': 'Rebook', 'url': ..., 'disabled': True/False}).
    """
    for action in actions:
        if action.get('label') == label:
            return action
    return {'url': '#', 'disabled': True}

@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})
