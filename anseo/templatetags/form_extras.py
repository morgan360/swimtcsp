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

@register.filter
def get_item(dictionary, key):
    """
    Usage: {{ my_dict|get_item:my_key }}
    Safely retrieves a value from a dict using a dynamic key.
    """
    return dictionary.get(key)

