"""Tests for the home app: the contact form's outgoing enquiry email, and the
home page notice banner.

For the contact form, the address staff reply to is the whole point. It used to
be swimming@tcsp.ie — the inbox the enquiry had just arrived in — so answering a
customer sent the reply back to ourselves.
"""
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from home.forms import ContactForm
from home.models import Announcement


class ContactFormEmailTests(TestCase):
    def setUp(self):
        # The live captcha would need a network round trip. Patching validate()
        # leaves the rest of the form's cleaning — including the honeypot and the
        # link limit — doing its real work.
        patcher = patch(
            'django_recaptcha.fields.ReCaptchaField.validate', return_value=None
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def submit(self, **overrides):
        data = {
            'name': 'Aoife Ryan',
            'email': 'aoife@example.com',
            'subject': 'Lesson times',
            'message': 'Is there a Saturday morning slot for a 6 year old?',
            'captcha': 'PASSED',
            'website': '',
        }
        data.update(overrides)
        return self.client.post(reverse('info_section', args=['contact']), data)

    def test_the_enquiry_reaches_the_support_inbox(self):
        self.submit()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['swimming@tcsp.ie'])

    def test_replying_answers_the_person_who_wrote_in(self):
        self.submit(email='parent@example.com')

        self.assertEqual(mail.outbox[0].reply_to, ['parent@example.com'])
        self.assertEqual(mail.outbox[0].message()['Reply-To'], 'parent@example.com')

    def test_the_default_reply_to_does_not_overwrite_the_enquirer(self):
        """The backend's default must lose to the address set here."""
        self.submit(email='parent@example.com')

        self.assertNotIn('swimming@tcsp.ie', mail.outbox[0].reply_to)

    def test_a_honeypot_submission_sends_nothing(self):
        response = self.submit(website='http://spam.example.com')

        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(response.status_code, 200)

    def test_a_honeypot_submission_is_told_it_succeeded(self):
        """The point of a honeypot: the bot must not learn it was caught, or
        whoever runs it just stops filling the field in."""
        response = self.submit(website='http://spam.example.com')

        self.assertTrue(response.context['success'])
        self.assertNotContains(response, 'Spam detected')

    def test_the_honeypot_value_survives_cleaning(self):
        """info_view is the only thing that acts on the honeypot, so the form
        has to hand it the value as submitted. A clean_website() that blanked or
        rejected it would send the bot's mail, or show it an error."""
        form = ContactForm(data={
            'name': 'Bot', 'email': 'bot@example.com', 'subject': 'x',
            'message': 'x', 'captcha': 'PASSED',
            'website': 'http://spam.example.com',
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['website'], 'http://spam.example.com')

    def test_a_message_full_of_links_sends_nothing(self):
        self.submit(message='http://a.example http://b.example http://c.example')

        self.assertEqual(len(mail.outbox), 0)


class AnnouncementOnHomePageTests(TestCase):
    """The notice is a conditional block, so cover both sides of the condition."""

    def test_no_announcement_page_still_renders(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_active_announcement_is_shown(self):
        Announcement.objects.create(
            title="Autumn term booking opens Mon 1 Sept",
            body="Places fill fast.",
            link_url="https://example.com/book",
            link_text="Book now",
            is_active=True,
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Autumn term booking opens Mon 1 Sept")
        self.assertContains(response, "https://example.com/book")
        self.assertContains(response, "Book now")

    def test_inactive_announcement_is_hidden(self):
        Announcement.objects.create(title="Draft notice", is_active=False)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Draft notice")

    def test_announcement_without_link_omits_button(self):
        """A URL with no label renders no button. Asserted on the URL rather
        than on CSS classes, so restyling the banner cannot make this pass by
        accident."""
        Announcement.objects.create(
            title="Pool closed Saturday",
            link_url="https://example.com/never-shown",
            link_text="",
            is_active=True,
        )
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Pool closed Saturday")
        self.assertNotContains(response, "https://example.com/never-shown")

    def test_current_returns_most_recently_updated_active(self):
        Announcement.objects.create(title="Older notice", is_active=True)
        newer = Announcement.objects.create(title="Newer notice", is_active=True)
        self.assertEqual(Announcement.current(), newer)


class AnnouncementExpiryTests(TestCase):
    """expires_on is the last day the notice shows, inclusive."""

    def setUp(self):
        self.today = timezone.localdate()

    def make(self, **kwargs):
        kwargs.setdefault("title", "Autumn term booking opens Mon 1 Sept")
        kwargs.setdefault("is_active", True)
        return Announcement.objects.create(**kwargs)

    def test_blank_expiry_never_expires(self):
        notice = self.make(expires_on=None)
        self.assertFalse(notice.has_expired)
        self.assertEqual(Announcement.current(), notice)

    def test_shows_on_its_final_day(self):
        notice = self.make(expires_on=self.today)
        self.assertFalse(notice.has_expired)
        self.assertEqual(Announcement.current(), notice)
        self.assertContains(self.client.get(reverse("home")), notice.title)

    def test_hidden_the_day_after(self):
        notice = self.make(expires_on=self.today - timedelta(days=1))
        self.assertTrue(notice.has_expired)
        self.assertIsNone(Announcement.current())
        self.assertNotContains(self.client.get(reverse("home")), notice.title)

    def test_future_expiry_still_shows(self):
        notice = self.make(expires_on=self.today + timedelta(days=7))
        self.assertEqual(Announcement.current(), notice)

    def test_expired_notice_does_not_mask_a_live_one(self):
        """The expired notice is newer, so it would win on ordering alone —
        it must be filtered out rather than blanking the banner."""
        live = self.make(title="Pool closed Saturday", expires_on=None)
        expired = self.make(
            title="Old notice", expires_on=self.today - timedelta(days=1)
        )
        self.assertGreater(expired.updated, live.updated)
        self.assertEqual(Announcement.current(), live)

    def test_expired_but_inactive_is_still_just_hidden(self):
        self.make(expires_on=self.today - timedelta(days=1), is_active=False)
        self.assertIsNone(Announcement.current())
