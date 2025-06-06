# Groups and Navigation Bar Logic

## 🔑 Overview

This document outlines the group-based navigation logic used in the TCSP Django application. User access is controlled via Django groups, which define what sections of the navbar are visible to different types of users.

## 👥 User Access Levels

### 1. Public Users (Unauthenticated)

* **Visible Nav Items**: Home, Public Swims, About, Contact, Sign up, Log in
* **No group membership required**

### 2. Guardians (Public Customers)

* **Groups**: `Guardian`, `guardian_temporary`
* **Visible Nav Items**: Public Lessons, Swimling Panel, My Account, Logout
* **Filter Used**: `is_guardian_user`

### 3. School-linked Customers

* **Groups**: `bishopgalvin`, `bishop_galvin`, `zion`
* **Visible Nav Items**: School Bookings, Register School, My Account, Logout
* **Filter Used**: `is_school_user`

### 4. Instructors and Admin Staff

* **Admin Groups** (access `Management` menu):

  * `administrator`, `Manager`, `pool_manager`, `pool_administrator`, `sh4_admin`, `desk_duties`, `editor`, `shop_manager`
* **Filter Used**: `is_admin_user`
* **Visible Nav Items**: Admin Panel, Dashboard, Analytics, Logout

## 🧰 Technical Implementation

### Template Filters

Custom filters defined in `group_filters.py`:

```python
@register.filter
def is_guardian_user(user):
    return user.groups.filter(name__in=["Guardian", "guardian_temporary"]).exists()

@register.filter
def is_school_user(user):
    return user.groups.filter(name__in=["bishopgalvin", "bishop_galvin", "zion"]).exists()

@register.filter
def is_admin_user(user):
    return user.groups.filter(name__in=[
        "administrator", "Manager", "pool_manager", "pool_administrator",
        "sh4_admin", "desk_duties", "editor", "shop_manager"
    ]).exists()
```

### Template Usage

These filters are used in `_navbar.html` to conditionally display menu sections:

```django
{% if user|is_guardian_user %} ... {% endif %}
{% if user|is_school_user %} ... {% endif %}
{% if user|is_admin_user %} ... {% endif %}
```

## 🧱 Notes

* Filters are loaded via `{% load group_filters %}`.
* Ensure `templatetags/group_filters.py` exists and is in a registered Django app.
* Run `python manage.py shell` to verify group names with: `Group.objects.values_list('name', flat=True)`.

## ✅ Maintenance Tips

* Use `Group.objects.get_or_create(name='...')` in a data migration or setup script to ensure groups exist.
* Avoid duplication of school names (e.g. `bishopgalvin` vs `bishop_galvin`) unless necessary.
* Consider consolidating naming conventions across all group entries.
