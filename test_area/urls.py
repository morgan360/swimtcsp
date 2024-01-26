from django.urls import path
from . import views
from .views import product_detail

app_name = 'test_area'

urlpatterns = [

    path('t_lessons/', views.t_lessons, name='t-lessons'),
    path('t_update_lesson_list/', views.t_update_lesson_list, name='t_update_lesson_list'),
    path('product_detail/<slug:slug>/', views.product_detail, name='product_detail'),
]