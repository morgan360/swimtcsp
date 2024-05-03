from django.urls import path
from .views import term_information, class_list_view, update_lessons, update_days, class_print

urlpatterns = [
    path('today/', term_information, name='term_information'),
    path('class/', class_list_view, name='class_list_view'),
    path('update-days', update_days, name='update-days'),
    path('update-lessons', update_lessons, name='update-lessons'),
    path('class-print/', class_print, name='class_print'),
]