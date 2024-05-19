# urls.py

from django.urls import path
from . import views

app_name = 'lessons'

urlpatterns = [
    path('lesson_list/', views.lesson_list, name='lesson_list'),
    path('update_lesson_list/', views.update_lesson_list, name='update_lesson_list'),
    path('add-new-swimling/', views.add_new_swimling, name='add_new_swimling'),
    path('load-new-swimling-form/<slug:product_slug>/', views.load_new_swimling_form, name='load_new_swimling_form'),
    path('product_detail/<int:id>/', views.product_detail, name='product_detail'),
    path('success/', views.swimling_success, name='swimling_success'),
    path('failure/', views.swimling_failure, name='swimling_failure'),
    path('<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('<int:id>/<slug:slug>/', views.product_detail, name='product_detail_again'),  # Ensure unique name if needed
]


