from django.urls import path
from . import views

app_name = 'schools_orders'

urlpatterns = [
    path('payment_process/', views.payment_process, name='payment_process'),
    # path('create/', views.order_create, name='order_create'),
]
