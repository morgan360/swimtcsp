from django.urls import path, include
from .views import home, info_view, management, check_guardian_access, getting_started

urlpatterns = [
    path('',home, name='home'),  # Add the view function 'home' here
    path('management/', management, name='management'),  # Add the view function 'home' here
    path('info/', info_view, name='info'),  # both
    path('info/<str:section>/', info_view, name='info_section'),  # about/contact
    path('api/check-guardian-access/', check_guardian_access, name='check_guardian_access'),
    path('getting-started/', getting_started, name='getting_started'),
]
