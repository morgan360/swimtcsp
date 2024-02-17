from django.urls import path
from . import views

app_name = 'schools_cart'

urlpatterns = [
    path('', views.cart_detail, name='sco_cart_detail'),
    path('add/<int:product_id>/', views.cart_add, name='sco_cart_add'),
    path('remove/<int:product_id>/', views.cart_remove,  name='cart_remove'),
    ]