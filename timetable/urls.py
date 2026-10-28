from django.urls import path
from .api import weekly_timetable, public_timetable, calendar_events
from .views import book_swim, calendar_page, tab_seen, timetable_grid

app_name = "timetable"
urlpatterns = [
    path('api/week/', weekly_timetable, name='weekly_timetable'),
    path('grid/', timetable_grid, name='timetable_grid'),
    path("api/public/", public_timetable, name="public_timetable"),
    path('calendar/', calendar_page, name='calendar_page'),
    path('calendar/events/', calendar_events, name='calendar_events'),
    path('seen/', tab_seen, name='tab_seen'),
    path('book/<int:product_id>/', book_swim, name='book_swim'),
]
