# User Flows, Permissions, and Recommendations

This document summarizes the current user roles, key navigation flows, and permission checks across the app. It also highlights inconsistencies and proposes updates for security, consistency, and UX.

## Roles and Groups

- Guardian: Access to the Swimling Dashboard and swimling management.
- Customer: Can book public swims, basic access.
- School: Access to school-related features once they are a guardian.
- Staff/Admin: Custom admin sites and staff-only tools.
- Coupons: Can issue coupons.
- Management: Full access.

Implementation notes:
- Template filters (loaded via `group_filters`) check membership using case-insensitive group names. Examples:
  - Guardian: `['guardian', 'Guardian']`
  - Customer: `['customer', 'Customer']`
  - School: `['zion', 'bishopgalvin', 'bishop_galvin', 'Schools']`

## Key Flows

### 1) Login and Redirects (allauth)

- The app uses Django Allauth and standard `?next=` query param for post-login redirects.

### 2) “Get Started” CTA (home page)

- Anonymous users: `Get Started` links to `account_login?next=/users/after-login/`.
- Post-login router `users:after_login` resolves roles:
  - Guardian → `swimling_dashboard:guardian_dashboard`
  - Non-guardian → `users:profile`

Why this is good:
- It provides a role-aware landing only for this CTA, while keeping other flows neutral.

Potential refinement:
- If you want this behavior only for this specific CTA, keep using the absolute path `/users/after-login/` in `next` so templates elsewhere can remain neutral (e.g., go to profile or home).

### 3) Swimling Dashboard Access (guardian only)

- View: `swimling_dashboard.views.guardian_dashboard`
- Decorators: `@login_required` and explicit guardian group check.
- On failure: redirects to `users:profile` with a flash message.

Recommendations:
- Include query params when redirecting to profile to improve UX:
  - `return redirect(f"{reverse('users:profile')}?guardian_required=true&from=/dashboard/")`
- Ensure every guardian-only view consistently uses the same guard pattern.

### 4) Become a Guardian

- View: `users.views.become_guardian_view` (POST toggles guardian membership).
- Redirect order: `redirect_to` POST field → `from` query param → dashboard default.

### 5) JS Guardian Check Helper (optional path)

- Endpoint: `home.views.check_guardian_access` (`/api/check-guardian-access/`).
- Returns JSON with `is_authenticated` and `is_guardian` booleans.

Status (implemented):
- Standardized to Guardian group membership (`['guardian', 'Guardian']`).

## Namespacing and URL Reversal

Status (implemented):
- `users/urls.py` sets `app_name = 'users'`.
- `core/urls.py` now includes users with `namespace='users'`:
  - `path('users/', include('users.urls', namespace='users'))`
This matches template/view usage of `users:...` and avoids resolution issues.

## Messaging UX

- A duplicate white-background modal for messages existed on the Profile page. It was removed to rely on the global message renderer in `templates/base/_base.html`.

Recommendations:
- Centralize messaging rendering (as in base template) and avoid per-page overlays unless necessary.
- Keep auto-fade timing and styling consistent.

## Security and Hardening

- Server-side authorization checks: Present on guardian dashboard. Ensure all privileged views follow the same pattern.
- CSRF: All POST-based role updates (e.g., become guardian) already use Django forms and CSRF tokens.
- URL construction: Prefer named URLs (`reverse`/`{% url %}`) for redirects to avoid relative path bugs (e.g., `/dashboard/users/profile`). Fixed in the guardian dashboard.
- Data exposure: `/api/check-guardian-access/` reveals minimal auth state. It’s acceptable, but consider avoiding role detail for unauthenticated users (always return `is_guardian: false` when unauthenticated, which is already the case).
- Group naming: Normalize to a single canonical group name per role (e.g., `guardian`, `customer`, `schools`). Use case-insensitive checks but avoid pluralization variants across the codebase.

## Actionable To-Do List

1) Namespace consistency — Done
   - `core/urls.py` updated to `namespace='users'`.

2) Group naming and checks — Done
   - `home.views.check_guardian_access` now uses Guardian group membership only.
   - Added shared helpers in `users.utils.roles` and migrated key checks:
     - `is_guardian(user, include_superuser=True)`
     - `is_customer(user, include_superuser=True)`
     - `is_school(user, include_superuser=True)`

3) Guardian dashboard redirect UX — Done
   - Non-guardians redirected to profile with `?guardian_required=true&from=/dashboard/`.

4) Keep `?next=` usage consistent
   - All login links should use `?next=...` and not custom params like `redirect_to`.

5) Logged-in access to Signup — Done
   - `CustomSignupView` now redirects authenticated users role‑aware:
     - Guardians → Swimling Dashboard
     - Others → Home

---
---

## 👥 Roles & Auth Conventions

- Roles are granted via Django groups. Canonical group names:
  - Guardian: `guardian` (case-insensitive match also accepts `Guardian`)
  - Customer: `customer` (also `Customer`)
  - School: `zion`, `bishopgalvin`, `bishop_galvin`, or `Schools` (legacy compatibility)

- Python helpers in `users/utils/roles.py`:
  - `is_guardian(user, include_superuser=True)`
  - `is_customer(user, include_superuser=True)`
  - `is_school(user, include_superuser=True)`
- Template filters exist in `home/templatetags/group_filters.py` for UI gating (e.g., `user|is_guardian_user`).

- Post‑login redirects use the standard `?next=` query param:
  - Example: `href="{% url 'account_login' %}?next={% url 'users:profile' %}"`
  - For role‑aware landing after login (used by the home Book Lessons” CTA):
    - `href="{% url 'account_login' %}?next=/users/after-login/"`
    - The router at `users/after-login/` sends guardians to `swimling_dashboard:guardian_dashboard` and others to `users:profile`.
