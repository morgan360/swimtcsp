from django.urls import path
from . import views

app_name = 'schools'

urlpatterns = [
    path('school_list/', views.school_list, name='school_list'),
    path('school_detail/<int:pk>/', views.school_detail, name='school_detail'),
    path('<slug:category_slug>/', views.school_list, name='schools_list_by_category'),
    path('<int:id>/<slug:slug>/', views.school_detail, name='schools_detail_again'),  # Optional: consolidate later
]
