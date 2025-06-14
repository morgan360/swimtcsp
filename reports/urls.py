from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('class/', views.class_list_view, name='class_list_view'),
    path('class/print/', views.class_print, name='class_print'),  # ✅ This is the key line
    path('update-lessons/', views.update_lessons, name='update-lessons'),
    path('update-days/', views.update_days, name='update-days'),
    path('enrollment/', views.enrollment_report, name='enrollment_report'),
    path('enrollment/data/', views.enrollment_report_data, name='enrollment-data'),
    path('term/', views.term_information, name='term_information'),
]