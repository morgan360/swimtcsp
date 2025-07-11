# users/admin.py
# Leave this file empty or just put a docstring
"""Admin definitions moved to custom_admins/usersadmin.py"""
from django.contrib import admin
from django.contrib.auth import get_user_model
from custom_admins.usersadmin import UserAdmin  # import the *class*, not the site

User = get_user_model()

try:
    admin.site.register(User, UserAdmin)
except admin.sites.AlreadyRegistered:
    pass