from django.urls import path
from .api import weekly_timetable, public_timetable
from .views import timetable_grid

app_name = "timetable"
urlpatterns = [
    path('api/week/', weekly_timetable, name='weekly_timetable'),
    path('grid/', timetable_grid, name='timetable_grid'),
    path("api/public/", public_timetable, name="public_timetable"),
]
