from django.urls import path
from . import views

app_name = 'swims_orders'

urlpatterns = [
    path('create/', views.order_create, name='order_create'),
]
