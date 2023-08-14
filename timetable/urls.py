from django.urls import path
from . import views

urlpatterns = [
    # Other URL patterns for the timetable app...
    path('', views.lessons_cal_view, name='lessons_cal_view'),
]
