# anseo/templatetags/form_extras.py
from django import template

register = template.Library()

@register.filter
def field(form, name):
    """
    Usage: {{ form|field:"status_123" }}
    Returns the bound field object for dynamic field names.
    """
    return form[name]
