from django.urls import path
from . import views

app_name = 'lessons'

urlpatterns = [
    path('lesson_list/', views.lesson_list, name='lesson_list'),
    path('update_lesson_list/', views.update_lesson_list, name='update_lesson_list'),
    path('product_detail/<int:id>/', views.product_detail, name='product_detail'),
    path('<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('<int:id>/<slug:slug>/', views.product_detail, name='product_detail_again'),  # Optional: clean up or merge this
]



