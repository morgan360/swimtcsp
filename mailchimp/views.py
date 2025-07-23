# mailchimp/views.py

from django.shortcuts import render
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from mailchimp.client import get_mailchimp_client

@staff_member_required  # restrict to logged-in admin users
def mailchimp_contacts_view(request):
    client = get_mailchimp_client()
    members = []

    try:
        response = client.lists.get_list_members_info(
            settings.MAILCHIMP_LIST_ID,
            count=1000  # max Mailchimp allows per request
        )
        members = response.get("members", [])
    except Exception as e:
        members = []
        error_message = str(e)
        return render(request, "mailchimp/contacts.html", {
            "error": error_message,
            "members": []
        })

    return render(request, "mailchimp/contacts.html", {
        "members": members
    })
