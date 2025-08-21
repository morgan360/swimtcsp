# APP/templatetags/progress_tags.py
from django import template

register = template.Library()

@register.filter
def get_item(mapping, key):
    """Safe dict lookup: {{ mydict|get_item:var_key }}"""
    if mapping is None:
        return None
    try:
        return mapping.get(key)
    except AttributeError:
        try:
            return mapping[key]
        except Exception:
            return None

@register.filter
def dict_get(d, key):
    """Alias: same as get_item, included if you prefer this name elsewhere."""
    return get_item(d, key)

@register.filter
def get_term_rating(ratings_dict, term_id):
    """Return ratings_dict[term_id] if present, else None."""
    if ratings_dict is None:
        return None
    try:
        return ratings_dict.get(term_id)
    except Exception:
        return None

@register.filter
def repeat(value, count):
    """Repeat a string N times: {{ '★'|repeat:3 }} -> ★★★"""
    try:
        return str(value) * int(count or 0)
    except Exception:
        return ""
