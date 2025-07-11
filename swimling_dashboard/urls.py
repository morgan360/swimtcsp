from django.urls import path
from . import views

app_name = 'swimling_dashboard'

urlpatterns = [
    path('', views.guardian_dashboard, name='guardian_dashboard'),

    # HTMX endpoints
    path('add-swimling/', views.add_swimling, name='add_swimling'),
    path('edit-swimling/<int:id>/', views.edit_swimling, name='edit-swimling'),
    path('refresh-rebooking/', views.refresh_rebooking_table, name='refresh_rebooking'),
    path('refresh-waiting-list/', views.refresh_waiting_list_panel, name='refresh_waiting_list'),
    path('refresh-school/', views.refresh_school_panel, name='refresh_school_panel'),
    path('checkout/school/<int:swimling_id>/<int:term_id>/', views.school_checkout, name='school_checkout'),
]
