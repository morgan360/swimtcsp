import hashlib
from django.conf import settings
from .client import get_mailchimp_client

def subscribe_user(email, first_name="", last_name=""):
    client = get_mailchimp_client()
    member_id = hashlib.md5(email.lower().encode()).hexdigest()
    try:
        response = client.lists.set_list_member(
            settings.MAILCHIMP_LIST_ID,
            member_id,
            {
                "email_address": email,
                "status_if_new": "subscribed",
                "merge_fields": {
                    "FNAME": first_name,
                    "LNAME": last_name,
                },
            },
        )
        return response
    except Exception as e:
        print(f"Mailchimp error: {e}")
        return None
