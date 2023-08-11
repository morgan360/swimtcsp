from django.urls import path
from . import views
from utils.webhooks import stripe_webhook

app_name = 'lessons_payment'

urlpatterns = [
    path('process/', views.payment_process, name='process'),
    path('completed/', views.payment_completed, name='completed'),
    path('canceled/', views.payment_canceled, name='canceled'),
    # path('webhook/', webhooks.stripe_webhook, name='stripe-webhook'),
    # path('webhook/', include('webhook_handler.urls'))
    path('webhook/', stripe_webhook, name='stripe_webhook'),
]