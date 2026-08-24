"""Tests for the term context processor and the outgoing-mail backend.

get_term_info runs on every page. Every date on Term is nullable, and
get_current_term() selects on start_date and end_date alone, so a term can be the
current one with its rebooking or booking date still blank. Comparing a date
against None raises, and from a context processor that takes down the whole site.
"""
from datetime import date, timedelta
from unittest.mock import patch

from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend as SMTPEmailBackend
from django.test import SimpleTestCase, TestCase, override_settings

from lessons_bookings.models import Term
from utils.context_processors import get_term_info
from utils.email_backend import ReplyToEmailBackend


class TermPhaseDateGuardTests(TestCase):
    def setUp(self):
        self.today = date.today()

    def info_for(self, term):
        """Run the context processor against one term, without touching the DB."""
        data = {
            'current_term': term,
            'next_term': None,
            'previous_term': None,
            'today': self.today,
        }
        with patch('utils.context_processors.get_term_context_data', return_value=data):
            return get_term_info(None)

    def term(self, **dates):
        defaults = {
            'start_date': self.today - timedelta(days=10),
            'end_date': self.today + timedelta(days=10),
            'rebooking_date': self.today - timedelta(days=5),
            'booking_date': self.today + timedelta(days=5),
        }
        defaults.update(dates)
        return Term(id=999, **defaults)

    def test_a_term_with_every_date_still_resolves_its_phase(self):
        """The guards must not change the answer when the dates are all present."""
        info = self.info_for(self.term())

        self.assertEqual(info['current_phase_id'], 'RB')
        self.assertEqual(info['active_modes'], ['BK', 'RB'])

    def test_before_rebooking_opens(self):
        info = self.info_for(self.term(rebooking_date=self.today + timedelta(days=2)))
        self.assertEqual(info['current_phase_id'], 'BK')

    def test_once_booking_is_open(self):
        info = self.info_for(self.term(
            rebooking_date=self.today - timedelta(days=5),
            booking_date=self.today - timedelta(days=1),
        ))
        self.assertEqual(info['current_phase_id'], 'BN')

    def test_a_missing_rebooking_date_does_not_raise(self):
        info = self.info_for(self.term(rebooking_date=None))

        self.assertIsNone(info['current_phase_id'])
        self.assertEqual(info['active_modes'], [])
        self.assertEqual(info['banners'], [])

    def test_a_missing_booking_date_does_not_raise(self):
        info = self.info_for(self.term(booking_date=None))

        self.assertIsNone(info['current_phase_id'])
        self.assertEqual(info['active_modes'], [])

    def test_a_missing_end_date_does_not_raise(self):
        info = self.info_for(self.term(
            rebooking_date=self.today - timedelta(days=5),
            booking_date=self.today - timedelta(days=1),
            end_date=None,
        ))

        self.assertIsNone(info['current_phase_id'])
        self.assertEqual(info['active_modes'], [])

    def test_a_term_with_no_dates_at_all_does_not_raise(self):
        info = self.info_for(self.term(
            start_date=None, end_date=None, rebooking_date=None, booking_date=None,
        ))

        self.assertIsNone(info['current_phase_id'])
        self.assertEqual(info['active_modes'], [])

    def test_no_current_term_does_not_raise(self):
        info = self.info_for(None)

        self.assertIsNone(info['current_phase_id'])
        self.assertEqual(info['current_term'], "No current term")

    def test_an_incomplete_term_closes_booking_rather_than_opening_it(self):
        """The safe direction. shopping_cart admits phase 'RB' only, so an empty
        phase refuses rebooking instead of letting it through."""
        info = self.info_for(self.term(booking_date=None))

        self.assertNotEqual(info['current_phase_id'], 'RB')
        self.assertNotEqual(info['current_phase_id'], 'BN')


class ReplyToBackendTests(SimpleTestCase):
    """The backend that keeps replies out of the send-only web@ mailbox.

    Django's test runner swaps EMAIL_BACKEND for locmem, so these drive the
    class directly and stub the SMTP send it inherits.
    """

    def send(self, *messages):
        """Run messages through the backend, returning them as it sent them."""
        backend = ReplyToEmailBackend()
        with patch.object(SMTPEmailBackend, 'send_messages', return_value=len(messages)):
            backend.send_messages(list(messages))
        return messages

    def message(self, **kwargs):
        kwargs.setdefault('subject', 'Order Confirmation')
        kwargs.setdefault('body', 'Thank you for your order.')
        kwargs.setdefault('from_email', 'web@tcsp.ie')
        kwargs.setdefault('to', ['parent@example.com'])
        return EmailMessage(**kwargs)

    @override_settings(DEFAULT_REPLY_TO_EMAIL='swimming@tcsp.ie')
    def test_a_message_without_a_reply_to_gets_the_default(self):
        message, = self.send(self.message())

        self.assertEqual(message.reply_to, ['swimming@tcsp.ie'])

    @override_settings(DEFAULT_REPLY_TO_EMAIL='swimming@tcsp.ie')
    def test_an_explicit_reply_to_is_left_alone(self):
        """home/views.py sets its own on the contact form, deliberately."""
        message, = self.send(self.message(reply_to=['someone@example.com']))

        self.assertEqual(message.reply_to, ['someone@example.com'])

    @override_settings(DEFAULT_REPLY_TO_EMAIL='swimming@tcsp.ie')
    def test_a_reply_to_set_as_a_header_is_not_duplicated(self):
        message, = self.send(self.message(headers={'Reply-To': 'header@example.com'}))

        self.assertEqual(message.reply_to, [])
        self.assertEqual(message.message()['Reply-To'], 'header@example.com')

    @override_settings(DEFAULT_REPLY_TO_EMAIL='swimming@tcsp.ie')
    def test_the_header_actually_reaches_the_built_message(self):
        """The point of the exercise: what the customer's mail client replies to."""
        message, = self.send(self.message())

        self.assertEqual(message.message()['Reply-To'], 'swimming@tcsp.ie')

    @override_settings(DEFAULT_REPLY_TO_EMAIL='')
    def test_an_empty_setting_switches_the_behaviour_off(self):
        message, = self.send(self.message())

        self.assertEqual(message.reply_to, [])

    @override_settings(DEFAULT_REPLY_TO_EMAIL='swimming@tcsp.ie')
    def test_every_message_in_a_batch_is_stamped(self):
        first, second = self.send(self.message(), self.message())

        self.assertEqual(first.reply_to, ['swimming@tcsp.ie'])
        self.assertEqual(second.reply_to, ['swimming@tcsp.ie'])
