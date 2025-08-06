# Architecture


## Django Apps

### 🔹 Built-in Apps
- `django.contrib.admin` – Admin interface
- `django.contrib.auth` – Authentication
- `django.contrib.sessions`, `messages`, `staticfiles`, `contenttypes`, `sites`

### 🔹 Third-Party Apps
- `allauth`, `allauth.account`, `allauth.socialaccount` – Login, OAuth
- `crispy_forms` – Form rendering
- `import_export` – CSV/XLSX import/export
- `phonenumber_field` – Phone number handling
- `django_filters` – Filtering in views and admin
- `django_admin_listfilter_dropdown` – Dropdown filters in admin
- `hijack`, `hijack.contrib.admin` – Admin login-as-user
- `widget_tweaks` – Modify form widgets in templates
- `django_browser_reload` – Auto-refresh in debug mode
- `tailwind`, `theme` – Tailwind integration and config
- `axes` – Brute force login protection

### 🔹 Custom Apps
- `users`, `home`, `lessons`, `lessons_orders`
- `swims`, `swims_orders`, `lessons_bookings`
- `timetable`, `reports`
- `schools`, `schools_bookings`, `schools_orders`
- `shopping_cart`, `boipa`, `waiting_list`
