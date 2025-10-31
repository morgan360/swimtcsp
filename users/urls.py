from django.urls import path, include
from . import views
from allauth.account.views import EmailVerificationSentView
from django.contrib.auth.decorators import login_required
from .views import join_schools_program

from users.views import CustomSignupView, my_bookings
from users.views import CustomSignupView, after_login


app_name = "users"

urlpatterns = [
    path("profile/", views.update_profile, name="profile"),
    path('accounts/', include('allauth.urls')),
    path('profile/become-guardian/', views.become_guardian_view, name='become_guardian'),
    path('<int:user_id>/', views.hijack_redirect, name='hijack_redirect'),
    path("join-schools/", join_schools_program, name="join_schools_program"),
    path("swimlings/", views.swimlings_list, name="swimlings_list"),
    path("swimlings/rows/", views.swimlings_list_rows, name="swimlings_list_rows"),
    path("swimlings/schools/", views.school_swimlings_list, name="school_swimlings_list"),
    path("swimlings/schools/rows/", views.school_swimlings_list_rows, name="school_swimlings_list_rows"),

    path("my-bookings/", my_bookings, name="my_bookings"),

    path('after-login/', after_login, name='after_login'),

]
