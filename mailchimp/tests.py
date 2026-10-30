from unittest.mock import patch

from django.test import TestCase

# Create your tests here.



class NewsletterSignupTests(TestCase):
    url = "/mailchimp/newsletter-signup/"

    def test_get_goes_home(self):
        self.assertRedirects(self.client.get(self.url), "/", fetch_redirect_response=False)

    def test_bad_email_goes_home_without_contacting_mailchimp(self):
        with patch("mailchimp.views.get_mailchimp_client") as client:
            response = self.client.post(self.url, {"email": "not-an-email"})
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        client.assert_not_called()
