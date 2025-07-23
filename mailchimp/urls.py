# mailchimp/urls.py

from django.urls import path
from .views import mailchimp_contacts_view
app_name = "mailchimp"

urlpatterns = [
    path("contacts/", mailchimp_contacts_view, name="contacts"),
]
