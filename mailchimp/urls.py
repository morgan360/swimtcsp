# mailchimp/urls.py

from django.urls import path
from .views import mailchimp_contacts_view
from .views import tag_email_for_test_campaign

app_name = "mailchimp"

urlpatterns = [
    path("contacts/", mailchimp_contacts_view, name="contacts"),
    path("test-campaign/", tag_email_for_test_campaign, name="test-campaign"),
]
