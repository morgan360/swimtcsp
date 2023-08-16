from django.urls import path,include
from .views import home, contact_us

urlpatterns = [
    path('contact/', contact_us, name='contact'),
    path('', home, name='home'),
    ]