"""Shared access-control decorators.

Several pages outside the admin show children's personal data — class sheets
carrying medical notes, progress reports, instructor notes. Instructors are not
``is_staff`` but are exactly who those pages are for, so a plain
``staff_member_required`` locks out the people who need them.
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from users.utils.roles import INSTRUCTOR_GROUPS, is_member_of_any


def staff_or_instructor_required(view_func):
    """Allow staff, superusers and instructors; send anyone else away."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        user = request.user
        if not getattr(user, "is_authenticated", False):
            return redirect_to_login(request.get_full_path())
        if user.is_superuser or user.is_staff or is_member_of_any(user, INSTRUCTOR_GROUPS):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied

    return _wrapped
