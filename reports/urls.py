from django.urls import path
from .views import show_todays_date, class_list_view, update_lessons, update_days, class_print

urlpatterns = [
    path('today/', show_todays_date, name='show_todays_data'),
    path('class/', class_list_view, name='class_list_view'),
    path('update-days', update_days, name='update-days'),
    path('update-lessons', update_lessons, name='update-lessons'),
    path('class-print/', class_print, name='class_print'),
]