from functools import wraps
from django.http import HttpResponseForbidden

def user_in_group(group_name):
    """
    Custom user check function to verify group membership.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and request.user.groups.filter(name=group_name).exists():
                print(f"User {request.user.username} is in group {group_name}")
                return view_func(request, *args, **kwargs)
            else:
                print(f"User {request.user.username} is in group {group_name}")
                return HttpResponseForbidden("Access denied. You must be logged in and in the appropriate group to access this page.")
        return _wrapped_view
    return decorator
