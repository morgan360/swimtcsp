# This file is used to create custom template tags
from django import template

register = template.Library()

@register.filter(name='in_group')
def in_group(user, group_name):
    return user.groups.filter(name__iexact=group_name).exists()

# High-level role filters
@register.filter(name='is_school_user')
def is_school_user(user):
    return user.groups.filter(name__in=['zion', 'bishopgalvin', 'bishop_galvin']).exists()

@register.filter(name='is_guardian_user')
def is_guardian_user(user):
    return user.groups.filter(name__iexact='guardian').exists()

@register.filter(name='is_admin_user')
def is_admin_user(user):
    return user.groups.filter(name__in=[
        'administrator', 'manager', 'pool_manager', 'pool_administrator',
        'desk_duties', 'sh4_admin', 'shop_manager', 'editor'
    ]).exists()

@register.filter(name='is_instructor_user')
def is_instructor_user(user):
    return user.groups.filter(name__in=['instructor', 'instructors']).exists()

@register.simple_tag
def user_role(user):
    if not user.is_authenticated:
        return 'public'
    elif user.groups.filter(name__iexact='guardian').exists():
        return 'guardian'
    elif user.groups.filter(name__in=['zion', 'bishopgalvin', 'bishop_galvin']).exists():
        return 'school'
    elif user.groups.filter(name__in=['instructor', 'instructors']).exists():
        return 'instructor'
    elif user.groups.filter(name__in=[
        'administrator', 'manager', 'pool_manager', 'pool_administrator',
        'desk_duties', 'sh4_admin', 'shop_manager', 'editor'
    ]).exists():
        return 'admin'
    return 'public'
# Add this new filter function
@register.filter(name='is_customer_user')
def is_customer_user(user):
    return user.groups.filter(name__iexact='customer').exists()