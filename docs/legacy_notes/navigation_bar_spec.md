# 🧭 TCSP Navigation Bar Schema

## Overview

The navigation bar dynamically changes based on the user's authentication status and group. This ensures clarity and relevance for each user type.

---

## 🔓 Public Users (Not Logged In)

| Menu Item         | Destination           | Notes                        |
|-------------------|------------------------|------------------------------|
| Home              | `/`                    | Site landing page            |
| Public Swim Info  | `/public-swims/`       | Timetable + general info     |
| Register          | `/accounts/signup/`    | Uses Allauth or custom logic |
| Login             | `/accounts/login/`     | Login with Django Allauth    |

---

## 🧑‍🎓 Swimming Lessons Customers (Logged In)

### 🟦 Type A: Standard Public Customer

| Menu Item        | Destination         | Notes                        |
|------------------|---------------------|------------------------------|
| Dashboard        | `/dashboard/`       | Overview of bookings         |
| Swimming Lessons | `/lessons/`         | Show lessons for their type  |
| My Children      | `/children/`        | CRUD child profiles          |
| My Bookings      | `/bookings/`        | View/manage bookings         |
| Logout           | `/accounts/logout/` | Clear session/logout         |

### 🟨 Type B: School-linked Customer

| Menu Item        | Destination            | Notes                    |
|------------------|------------------------|--------------------------|
| School Lessons   | `/school/`             | Bookings via roll number |
| Register School  | `/school/register/`    | Uses school-specific flow|
| My Children      | `/children/`           | Still relevant           |
| Logout           | `/accounts/logout/`    |                          |

> 🧩 **Note**: Type B users should **not** see the standard public lesson options.

---

## 🛠️ Management / Admin Users

| Menu Item        | Destination              | Notes                          |
|------------------|--------------------------|--------------------------------|
| Admin Panel      | `/admin/`                | Django admin                   |
| Session Manager  | `/admin/sessions/`       | Manage all swim sessions       |
| User Management  | `/admin/auth/user/`      | Manage users                   |
| Reports          | `/reports/`              | Custom finance/usage reports   |
| Logout           | `/accounts/logout/`      |                                |

> 🔐 **Menus** can be conditionally shown using  
> `{% if user.is_staff %}`, `{% if user.groups %}`, or custom template tags.

---

## 💡 Implementation Notes

- Uses **Bulma dropdowns**
- Interactive elements powered by **HTMX**
- Use `{% if %}` to hide/show appropriate menus
- Menu toggle (expanded/collapsed) with **Alpine.js**