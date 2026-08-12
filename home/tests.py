"""Tests for the contact form's outgoing enquiry email.

The address staff reply to is the whole point of this form. It used to be
swimming@tcsp.ie — the inbox the enquiry had just arrived in — so answering a
customer sent the reply back to ourselves.
"""
from unittest.mock import patch

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from home.forms import ContactForm


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
