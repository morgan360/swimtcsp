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


from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings

from mailchimp import services

MAILCHIMP = {"MAILCHIMP_API_KEY": "key-us1", "MAILCHIMP_LIST_ID": "list"}


@override_settings(**MAILCHIMP)
@patch("mailchimp.services.get_mailchimp_client")
class ConsentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="parent@example.com", password="pw-123456!", first_name="Ann", last_name="Byrne")

    def test_ticking_the_box_records_consent_and_subscribes(self, get_client):
        get_client.return_value.lists.set_list_member.return_value = {"status": "subscribed"}
        services.record_opt_in(self.user, True)
        self.user.refresh_from_db()
        self.assertTrue(self.user.marketing_opt_in)
        self.assertIsNotNone(self.user.marketing_opt_in_at)
        get_client.return_value.lists.set_list_member.assert_called_once()

    def test_a_previous_unsubscriber_is_asked_to_confirm(self, get_client):
        lists = get_client.return_value.lists
        lists.set_list_member.side_effect = [{"status": "unsubscribed"}, {"status": "pending"}]
        services.record_opt_in(self.user, True)
        self.assertEqual(lists.set_list_member.call_args_list[1].args[2]["status"], "pending")

    def test_mailchimp_down_still_saves_the_choice(self, get_client):
        get_client.return_value.lists.set_list_member.side_effect = Exception("down")
        services.record_opt_in(self.user, True)
        self.user.refresh_from_db()
        self.assertTrue(self.user.marketing_opt_in)

    def test_profile_form_unticking_unsubscribes(self, get_client):
        from users.forms import UserForm
        services.record_opt_in(self.user, True, push=False)
        form = UserForm({"first_name": "Ann", "last_name": "Byrne", "mobile_phone": ""}, instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.refresh_from_db()
        self.assertFalse(self.user.marketing_opt_in)
        get_client.return_value.lists.update_list_member.assert_called_once()

    def test_profile_form_shows_current_choice(self, _client):
        from users.forms import UserForm
        services.record_opt_in(self.user, True, push=False)
        self.assertTrue(UserForm(instance=self.user)["marketing_opt_in"].value())


@override_settings(**MAILCHIMP)
@patch("mailchimp.services.get_mailchimp_client")
class SyncTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.opted_in = User.objects.create_user(email="yes@example.com", password="x", first_name="Y",
                                                 marketing_opt_in=True)
        self.not_asked = User.objects.create_user(email="no@example.com", password="x", first_name="N")

    def test_only_opted_in_accounts_are_sent(self, get_client):
        get_client.return_value.lists.set_list_member.return_value = {"status": "subscribed"}
        call_command("sync_mailchimp", stdout=StringIO())
        sent = [c.args[2]["email_address"] for c in get_client.return_value.lists.set_list_member.call_args_list]
        self.assertEqual(sent, ["yes@example.com"])

    def test_tags_use_our_prefix_and_reflect_orders(self, get_client):
        from lessons_orders.models import Order
        Order.objects.create(user=self.opted_in, paid=True, amount=10)
        get_client.return_value.lists.set_list_member.return_value = {"status": "subscribed"}
        call_command("sync_mailchimp", stdout=StringIO())
        tags = get_client.return_value.lists.update_list_member_tags.call_args.args[2]["tags"]
        self.assertTrue(all(t["name"].startswith(services.TAG_PREFIX) for t in tags))
        self.assertIn({"name": services.TAG_CUSTOMER, "status": "active"}, tags)
        self.assertIn({"name": services.TAG_BOOKED, "status": "inactive"}, tags)

    def test_unsubscribed_in_mailchimp_turns_the_box_off_here(self, get_client):
        get_client.return_value.lists.set_list_member.return_value = {"status": "unsubscribed"}
        call_command("sync_mailchimp", stdout=StringIO())
        self.opted_in.refresh_from_db()
        self.assertFalse(self.opted_in.marketing_opt_in)
        get_client.return_value.lists.update_list_member_tags.assert_not_called()

    def test_dry_run_makes_no_calls(self, get_client):
        call_command("sync_mailchimp", "--dry-run", stdout=StringIO())
        get_client.assert_not_called()


@override_settings(**MAILCHIMP)
class NewsletterConsentTests(TestCase):
    def test_signing_up_with_your_account_email_ticks_your_box(self):
        user = get_user_model().objects.create_user(email="parent@example.com", password="x", first_name="A")
        with patch("mailchimp.services.get_mailchimp_client") as get_client:
            get_client.return_value.lists.set_list_member.return_value = {"status": "subscribed"}
            self.client.post("/mailchimp/newsletter-signup/", {"email": "Parent@example.com"})
        user.refresh_from_db()
        self.assertTrue(user.marketing_opt_in)
