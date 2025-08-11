from django import template

register = template.Library()

@register.filter
def get_term_rating(ratings_dict, term_number):
    return ratings_dict.get(term_number)

@register.filter
def repeat(value, count):
    return value * int(count) if count else ''

@register.filter
def dict_get(d, key):
    try:
        return d.get(key)
    except Exception:
        return None

# instructors/templatetags/progress_tags.py
from django import template

register = template.Library()

@register.filter
def get_item(mapping, key):
    """Safe dict lookup in templates: {{ mydict|get_item:var_key }}"""
    try:
        return mapping.get(key)
    except AttributeError:
        return None

@register.filter
def repeat(s, n):
    """Repeat a string N times: {{ "★"|repeat:3 }} -> ★★★"""
    try:
        return str(s) * int(n or 0)
    except Exception:
        return ""

@register.filter
def get_term_rating(ratings_dict, term_id):
    """Returns the rating for a given term from a nested dict."""
    return ratings_dict.get(term_id)
