from django.urls import path
from . import views

app_name = 'shopping_cart'

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:product_id>/<str:type>/', views.cart_add, name='cart_add'),
    path('remove/<int:product_id>/<str:type>/<int:swimling_id>/', views.cart_remove, name='cart_remove'),
    path('payment-process/', views.payment_process, name='payment_process'),
    ]