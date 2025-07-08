from django.urls import path, include
from . import views
from allauth.account.views import EmailVerificationSentView
from django.contrib.auth.decorators import login_required

app_name = "users"

urlpatterns = [
    path("profile/", views.update_profile, name="profile"),
    path('accounts/', include('allauth.urls')),
    path('profile/become-guardian/', views.become_guardian_view, name='become_guardian'),
    path('<int:user_id>/', views.hijack_redirect, name='hijack_redirect'),
]
