# dashboard/urls.py
from django.urls import path
from . import views
app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('public-swims/', views.public_swims, name='dashboard_public_swims'),
    path('public-swims/attendance/', views.public_swims_attendance, name='dashboard_public_swims_attendance'),
    path('lessons/', views.lessons, name='dashboard_lessons'),
    path('admin_lessons_list/', views.admin_lessons_list, name='admin_lessons_list'),
    path('admin_lessons_list/rows/', views.admin_lessons_list_rows, name='admin_lessons_list_rows'),
    path('lessons/<int:lesson_id>/history/', views.lessons_history, name='lessons_history'),
    path('schools/', views.schools, name='dashboard_schools'),
    path('schools/lessons/', views.admin_school_lessons_list, name='admin_school_lessons_list'),
    path('schools/lessons/rows/', views.admin_school_lessons_list_rows, name='admin_school_lessons_list_rows'),
    path('schools/lessons/<int:lesson_id>/', views.admin_school_lesson_detail, name='admin_school_lesson_detail'),
    path('orders/', views.orders, name='dashboard_orders'),
    path('orders/history/', views.orders_history, name='orders_history'),
    path('orders/bookings/', views.bookings_overview, name='bookings_overview'),
    path('general/', views.general_admin, name='dashboard_general'),
    path('users/', views.user_management, name='user_management'),
    path('users/list/', views.user_list, name='user_list'),
    path('management/', views.management, name='management'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/swimlings/', views.view_user_swimlings, name='view_user_swimlings'),
]
