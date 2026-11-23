from django.urls import path, reverse_lazy
from django.views.generic import RedirectView
from . import views

app_name = 'schools'

urlpatterns = [
    path('school_list/', views.school_list, name='school_list'),
    path('school_detail/<int:pk>/', views.school_detail, name='school_detail'),
    # The menu's "School Dashboard" link. School bookings live on the guardian
    # dashboard; before this the slug route below caught it and returned a 500.
    path('school_dashboard/', RedirectView.as_view(url=reverse_lazy('swimling_dashboard:guardian_dashboard')),
         name='school_dashboard'),
    path('<slug:category_slug>/', views.school_list, name='schools_list_by_category'),
    path('<int:id>/<slug:slug>/', views.school_detail, name='schools_detail_again'),  # Optional: consolidate later
]
