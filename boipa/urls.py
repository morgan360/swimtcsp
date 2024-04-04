from django.urls import path
from . import views

app_name = 'boipa'

urlpatterns = [
    path('initiate-payment-session/<str:order_ref>/<str:total_price>/', views.initiate_boipa_payment_session,
         name='initiate_payment_session'),
    # path('load-payment-form/', views.load_payment_form, name='load_payment_form'),
    # path('error/', views.error_view, name='error'),
    path('payment-notification/', views.payment_notification, name='payment_notification'),
    path('payment-response/', views.payment_response, name='payment_response'),
]