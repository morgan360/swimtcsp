# navigation/templatetags/navigation_tags.py
from django import template
from navigation.models import MenuGroup, MenuItem

register = template.Library()

@register.simple_tag(takes_context=True)
def drawer_menu(context):
    """
    Returns a dictionary of visible MenuGroups and their filtered MenuItems for the current user.
    Usage: {% drawer_menu as menu %}
    """
    user = context['request'].user
    menu = {}

    for group in MenuGroup.objects.prefetch_related('items').all():
        items = []
        for item in group.items.all():
            if item.requires_login and not user.is_authenticated:
                continue
            if item.requires_staff and not user.is_staff:
                continue
            if item.required_groups.exists() and not user.groups.filter(id__in=item.required_groups.values_list('id', flat=True)).exists():
                continue
            items.append(item)
        if items:
            menu[group.name] = items

    return menu
