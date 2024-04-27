from django.urls import path
from . import views

app_name = 'schools'

urlpatterns = [
    path('school_list/', views.school_list, name='school_list'),
    path('add-new-swimling/', views.add_new_swimling, name='add_new_swimling'),
    path('load-new-swimling-form/<slug:product_slug>/', views.load_new_swimling_form, name='load_new_swimling_form'),
    path('school_detail/<int:pk>/', views.school_detail, name='school_detail'),
    # Place specific URLs before the more general category_slug pattern
    path('success/', views.swimling_success, name='swimling_success'),
    path('failure/', views.swimling_failure, name='swimling_failure'),
    path('<slug:category_slug>/', views.school_list, name='schools_list_by_category'),
    path('<int:id>/<slug:slug>/', views.school_detail, name='schools_detail_again'),  # Ensure unique name if needed
]

