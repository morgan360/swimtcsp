# urls.py
from django.urls import path
from .views import RegistrationWizardView, instructor_assignments

app_name = 'lessons_bookings'

urlpatterns = [
    path('register/', RegistrationWizardView.as_view(), name='registration_wizard'),
    path('instructors/', instructor_assignments, name='instructor_assignments'),
]
