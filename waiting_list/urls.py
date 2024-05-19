from django.urls import path
from . import views

app_name = 'waiting_list'

urlpatterns = [
    path('join/<int:product_id>/', views.join_waiting_list, name='join_waiting_list'),
    path('manage/', views.manage_waiting_list, name='manage_waiting_list'),
    path('notify/<int:waiting_list_id>/', views.notify_customer, name='notify_customer'),
    path('success/', views.waiting_list_success, name='waiting_list_success'),
]
