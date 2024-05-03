from django.urls import path, include
from . import views
from allauth.account.views import EmailVerificationSentView
from django.contrib.auth.decorators import login_required

app_name = "users"

urlpatterns = [
    path("profile/", views.update_profile, name="profile"),
    path("swimling_mgmt/", views.swimling_mgmt, name="swimling_mgmt"),
    path('edit_swimling/<int:id>/', views.edit_swimling, name='edit-swimling'),
    path('add_new_swimling/', views.add_new_swimling, name='add_new_swimling'),
    path('accounts/', include('allauth.urls')),
    path('<int:user_id>/', views.hijack_redirect, name='hijack_redirect'),
]
