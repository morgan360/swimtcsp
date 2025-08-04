# urls.py
from django.urls import path
from .views import RegistrationWizardView

app_name = 'lessons_bookings'

urlpatterns = [
    path('register/', RegistrationWizardView.as_view(), name='registration_wizard'),
]
