# dashboard/urls.py
from django.urls import path
from . import views
app_name = 'dashboard'
urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('public-swims/', views.public_swims, name='dashboard_public_swims'),
    path('lessons/', views.lessons, name='dashboard_lessons'),
    path('schools/', views.schools, name='dashboard_schools'),
    path('orders/', views.orders, name='dashboard_orders'),
    path('general/', views.general_admin, name='dashboard_general'),
]
