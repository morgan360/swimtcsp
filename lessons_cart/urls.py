from django.urls import path
from . import views

app_name = 'lessons_cart'

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('remove/<int:product_id>/<int:swimling_id>/', views.cart_remove, name='cart_remove'),
    ]