# mailchimp/views.py

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from mailchimp.client import get_mailchimp_client
from django import forms
from django.contrib import messages
from .forms import TestCampaignForm
import hashlib

@staff_member_required
def mailchimp_contacts_view(request):
    client = get_mailchimp_client()

    try:
        page = int(request.GET.get("page", 1))
        per_page = 50
        offset = (page - 1) * per_page

        response = client.lists.get_list_members_info(
            settings.MAILCHIMP_LIST_ID,
            count=per_page,
            offset=offset
        )
        members = response.get("members", [])
        total = response.get("total_items", 0)
    except Exception as e:
        return render(request, "mailchimp/contacts.html", {
            "error": str(e),
            "members": [],
        })

    num_pages = (total + per_page - 1) // per_page

    start_index = offset + 1
    end_index = offset + len(members)
    return render(request, "mailchimp/contacts.html", {
        "members": members,
        "page": page,
        "num_pages": num_pages,
        "start_index": start_index,
        "end_index": end_index,
        "total": total,
    })


# Test Mailchimp Campaign
@staff_member_required
def tag_email_for_test_campaign(request):
    if request.method == "POST":
        form = TestCampaignForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            member_id = hashlib.md5(email.lower().encode()).hexdigest()
            tag_name = "TestCampaign"

            client = get_mailchimp_client()
            try:
                # Ensure contact exists
                client.lists.set_list_member(
                    settings.MAILCHIMP_LIST_ID,
                    member_id,
                    {
                        "email_address": email,
                        "status_if_new": "subscribed",
                        "merge_fields": {},
                    }
                )

                # Tag them
                client.lists.update_list_member_tags(
                    settings.MAILCHIMP_LIST_ID,
                    member_id,
                    {"tags": [{"name": tag_name, "status": "active"}]}
                )

                messages.success(request, f"{email} tagged for TestCampaign.")

            except Exception as e:
                error_msg = getattr(e, "text", str(e))  # Mailchimp errors sometimes store JSON in .text
                messages.error(request, f"Mailchimp error: {error_msg}")

    else:
        form = TestCampaignForm()

    return render(request, "mailchimp/test_campaign.html", {"form": form})
