from django.urls import path, include
from .views import home, contact_us, management

urlpatterns = [
    path('contact/', contact_us, name='contact'),
    path('', home, name='home'),  # Add the view function 'home' here
    path('management/', management, name='management'),  # Add the view function 'home' here
]
