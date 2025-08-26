# dashboard/urls.py
from django.urls import path
from . import views
app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('public-swims/', views.public_swims, name='dashboard_public_swims'),
    path('lessons/', views.lessons, name='dashboard_lessons'),
    path('admin_lessons_list/', views.admin_lessons_list, name='admin_lessons_list'),
    path('lessons/<int:lesson_id>/history/', views.lessons_history, name='lessons_history'),
    path('schools/', views.schools, name='dashboard_schools'),
    path('orders/', views.orders, name='dashboard_orders'),
    path('general/', views.general_admin, name='dashboard_general'),
    path('users/', views.user_management, name='user_management'),
    path('users/list/', views.user_list, name='user_list'),
    path('management/', views.management, name='management'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/swimlings/', views.view_user_swimlings, name='view_user_swimlings'),
]
