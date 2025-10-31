from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('class/', views.class_list_view, name='class_list_view'),
    path('class/print/', views.class_print, name='class_print'),  # ✅ This is the key line
    path('school-class/', views.school_class_list_view, name='school_class_list_view'),
    path('school-class/print/', views.school_class_print, name='school_class_print'),
    path('school-class/update-filters/', views.update_school_filters, name='update-school-filters'),
    path('school-class/update-times/', views.update_school_times, name='update-school-times'),
    path('school-class/update-lessons/', views.update_school_lessons, name='update-school-lessons'),
    path('update-lessons/', views.update_lessons, name='update-lessons'),
    path('update-days/', views.update_days, name='update-days'),
    path('update-times/', views.update_times, name='update-times'),
    path('enrollment/', views.enrollment_report, name='enrollment_report'),
    path('enrollment/data/', views.enrollment_report_data, name='enrollment-data'),
    path('enrollment/schools/', views.school_enrollment_report, name='school_enrollment_report'),
    path('enrollment/schools/data/', views.school_enrollment_report_data, name='school_enrollment_report_data'),
    path('term/', views.term_information, name='term_information'),
]
