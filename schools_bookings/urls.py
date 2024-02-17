# urls.py
from django.urls import path
from .views import RegistrationWizardView

app_name = 'schools_bookings'

urlpatterns = [
    path('register/', RegistrationWizardView.as_view(), name='registration_wizard'),
    # path('registration_success/', registration_success_view, name='registration_success'),
]
