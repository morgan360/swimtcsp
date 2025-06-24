from django.urls import path, include
from .views import home, info_view, management
urlpatterns = [
    path('',home, name='home'),  # Add the view function 'home' here
    path('management/', management, name='management'),  # Add the view function 'home' here
    path('info/', info_view, name='info'),  # both
    path('info/<str:section>/', info_view, name='info_section'),  # about/contact
]
