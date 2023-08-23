from django.urls import path
from . import views

app_name = 'lessons'

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('category/', views.category_list, name='categories'),
    path('programs/', views.programs, name='programs'),
    path('lessons/', views.lesson_list, name='lessons'),
    path('<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('<int:id>/<slug:slug>/', views.product_detail,  name='product_detail'),
]
