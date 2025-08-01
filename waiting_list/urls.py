from django.urls import path
from . import views

app_name = 'waiting_list'

urlpatterns = [
    path('join/<int:product_id>/', views.join_waiting_list, name='join_waiting_list'),
    path('manage/', views.manage_waiting_list, name='manage_waiting_list'),
    path('notify/<int:waiting_list_id>/', views.notify_customer, name='notify_customer'),
    path('start/', views.enter_email_for_waiting_list, name='start'),
    path('signup/', views.public_waiting_list_signup, name='public_signup'),
    path('success/', views.waiting_list_success, name='waiting_list_success'),
    path('remove/<int:id>/', views.remove_waiting_list_entry, name='remove'),
]
