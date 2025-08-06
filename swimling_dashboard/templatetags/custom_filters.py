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
    Match a next-term lesson based on the current lesson.
    Adjust matching logic as needed.
    """
    for lesson in next_lessons:
        if lesson.name == current_lesson.name:
            return lesson
    return None

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
