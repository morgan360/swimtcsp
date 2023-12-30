from django.urls import path
from .views import show_todays_date

urlpatterns = [
    path('today/', show_todays_date, name='show_todays_date'),
]