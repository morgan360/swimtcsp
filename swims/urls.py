from django.urls import path
from . import views

app_name = 'swims'

urlpatterns = [
    path('calculate_total/', views.calculate_total, name='calculate_total'),
    path('', views.product_list, name='product_list'),
    path('<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('<int:id>/<slug:slug>/', views.product_detail,  name='product_detail'),
    path('product/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),


]

