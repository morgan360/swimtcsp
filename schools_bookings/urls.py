# urls.py
from django.urls import path
from .views import RegistrationWizardView, book_lesson

app_name = 'schools_bookings'

urlpatterns = [
    path('register/', RegistrationWizardView.as_view(), name='registration_wizard'),
    path('book/<int:swimling_id>/<int:term_id>/', book_lesson, name='book_lesson'),  # ✅ NEW
]
