import mailchimp_marketing as MailchimpMarketing
from django.conf import settings

def get_mailchimp_client():
    client = MailchimpMarketing.Client()
    client.set_config({
        "api_key": settings.MAILCHIMP_API_KEY,
        "server": settings.MAILCHIMP_SERVER_PREFIX,
    })
    return client
