from typing import Iterable


# Canonical group names for roles
GUARDIAN_GROUPS: tuple[str, ...] = ("guardian", "Guardian")
CUSTOMER_GROUPS: tuple[str, ...] = ("customer", "Customer")
# School users currently map to several names in group_filters
SCHOOL_GROUPS: tuple[str, ...] = ("zion", "bishopgalvin", "bishop_galvin", "Schools")


def is_member_of_any(user, groups: Iterable[str]) -> bool:
    """Return True if authenticated user belongs to any of the given groups."""
    return bool(getattr(user, "is_authenticated", False) and user.groups.filter(name__in=list(groups)).exists())


def is_guardian(user, include_superuser: bool = True) -> bool:
    """Centralized guardian check used across views and APIs.

    - Treats superusers as guardians by default (override via include_superuser=False).
    - Uses group membership only (single source of truth).
    """
    if include_superuser and getattr(user, "is_superuser", False):
        return True
    return is_member_of_any(user, GUARDIAN_GROUPS)


def is_customer(user, include_superuser: bool = True) -> bool:
    """Customer role check.

    - Superusers can be treated as customers.
    """
    if include_superuser and getattr(user, "is_superuser", False):
        return True
    return is_member_of_any(user, CUSTOMER_GROUPS)


def is_school(user, include_superuser: bool = True) -> bool:
    """School role check (supports legacy group names)."""
    if include_superuser and getattr(user, "is_superuser", False):
        return True
    return is_member_of_any(user, SCHOOL_GROUPS)
