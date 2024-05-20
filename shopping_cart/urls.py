from django.urls import path
from . import views

app_name = 'shopping_cart'

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('review-rebooking/<int:swimling_id>/<int:product_id>/', views.review_rebooking, name='review_rebooking'),
    path('cart/add/<int:product_id>/<str:type>/', views.cart_add, name='cart_add'),
    path('remove/<int:product_id>/<str:type>/<int:swimling_id>/', views.cart_remove, name='cart_remove'),
    path('payment-process/', views.payment_process, name='payment_process'),
    path('direct_order/<int:swimling_id>/<int:school_id>/<int:active_term>/', views.direct_order, name='direct_order'),
    path('confirm-rebooking/<int:swimling_id>/<int:product_id>/', views.confirm_rebooking, name='confirm_rebooking'),
    path('review_waiting_list_booking/<int:swimling_id>/<int:product_id>/', views.review_waiting_list_booking,
         name='review_waiting_list_booking'),
    path('confirm_waiting_list_booking/<int:swimling_id>/<int:product_id>/', views.confirm_waiting_list_booking,
         name='confirm_waiting_list_booking'),
]
