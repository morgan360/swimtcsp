from django.urls import path
from .views import (
    term_information, 
    class_list_view, 
    update_lessons, 
    update_days, 
    class_print,
    enrollment_report,
    enrollment_report_data
)

app_name = 'reports'

urlpatterns = [
    path('today/', term_information, name='term_information'),
    path('class/', class_list_view, name='class_list_view'),
    path('update-days', update_days, name='update-days'),
    path('update-lessons', update_lessons, name='update-lessons'),
    path('class-print/', class_print, name='class_print'),
    
    # New enrollment report URLs
    path('enrollment/', enrollment_report, name='enrollment_report'),
    path('enrollment/data/', enrollment_report_data, name='enrollment_report_data'),
]