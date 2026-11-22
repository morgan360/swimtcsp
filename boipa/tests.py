"""The payment callbacks must not believe what they are sent.

On 22 Nov 2026 a script marked a real customer's unpaid swim order paid (and
sent them three confirmation emails) by posting status=CAPTURED with the order's
reference. These replay that attack, and check a real payment still goes through.
"""
import json
from datetime import date, time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from boipa import utils
from boipa.models import SwimOrderPaymentNotification
from security.models import SecurityIncident
from swims.models import PublicSwimCategory, PublicSwimProduct
from swims_orders.models import Order

REAL_TX = "TRN_nxP3BxRKhPOypvXG0H8C5WY_5_1795304199"


def boipa_says(status="CAPTURED", reference=None):
    """Patch BOIPA's transaction lookup. reference=None means 'no such transaction'."""
    if reference is None:
        return patch("boipa.utils._fetch_new_api", return_value=None)
    return patch("boipa.utils._fetch_new_api", return_value={
        "captured": status == "CAPTURED", "status": status, "amount": Decimal("7"),
        "currency": "EUR", "raw": {"reference": reference},
    })


@override_settings(CHATBOT_ABUSE_ALERT_EMAIL="owner@example.com")
class PaymentConfirmationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        user = get_user_model().objects.create_user(email="c@example.com", password="x")
        category = PublicSwimCategory.objects.create(name="Public Swim", slug="public-swim")
        product = PublicSwimProduct.objects.create(
            category=category, day_of_week=6, start_time=time(15), end_time=time(16), num_places=50)
        self.order = Order.objects.create(user=user, product=product, booking=date(2026, 11, 22),
                                          amount=Decimal("7.00"), paid=False)
        self.ref = f"swims_{self.order.id}_1795342279"
        self.sent = patch("boipa.views.send_order_email").start()
        self.addCleanup(patch.stopall)

    def _notify(self, **data):
        return self.client.post(reverse("boipa:payment_notification"),
                                data=json.dumps(data), content_type="application/json")

    def _return(self, **params):
        return self.client.get(reverse("boipa:payment_response"), params)

    def assertStillUnpaid(self):
        self.order.refresh_from_db()
        self.assertFalse(self.order.paid)
        self.sent.assert_not_called()

    # --- the 22 Nov attack, verbatim ---

    def test_forged_notification_does_not_mark_paid(self):
        with boipa_says(reference=None):
            response = self._notify(reference=self.ref, id="FORGED_TEST_TXN_QA1", status="CAPTURED", amount="700")
        self.assertEqual(response.status_code, 400)
        self.assertStillUnpaid()
        self.assertFalse(SwimOrderPaymentNotification.objects.filter(status="CAPTURED").exists())
        self.assertEqual(SecurityIncident.objects.filter(kind="payment_rejected").count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("NOT marked paid", mail.outbox[0].body)

    def test_injection_in_the_transaction_id_never_reaches_boipa(self):
        with patch("boipa.utils._fetch_new_api") as lookup:
            self._notify(reference=self.ref, id="a'\\%_é🚀-1 OR 1=1--", status="CAPTURED")
            self._notify(reference=self.ref, id={"$ne": None}, status="CAPTURED")
            self._notify(reference=self.ref, id="../../accounts", status="CAPTURED")
            lookup.assert_not_called()
        self.assertStillUnpaid()

    def test_object_status_no_longer_crashes(self):
        with boipa_says(reference=None):
            response = self._notify(reference=self.ref, id="X1", status={"$ne": None})
        self.assertLess(response.status_code, 500)

    def test_forged_return_url_does_not_mark_paid(self):
        with boipa_says(reference=None):
            response = self._return(reference=self.ref, id="TRN_made_up", status="CAPTURED")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"confirming your payment", response.content)
        self.assertStillUnpaid()
        self.assertFalse(SwimOrderPaymentNotification.objects.exists())

    def test_someone_elses_real_payment_cannot_be_replayed(self):
        with boipa_says(reference="swims_999_1795304199"):
            self._return(reference=self.ref, id=REAL_TX, status="CAPTURED")
            self._notify(reference=self.ref, id=REAL_TX, status="CAPTURED")
        self.assertStillUnpaid()

    def test_declined_at_boipa_is_not_paid(self):
        with boipa_says(status="DECLINED", reference=self.ref):
            self._return(reference=self.ref, id=REAL_TX, status="CAPTURED")
        self.assertStillUnpaid()

    # --- real payments still work ---

    def test_confirmed_payment_on_return_marks_paid(self):
        with boipa_says(reference=self.ref):
            response = self._return(reference=self.ref, id=REAL_TX, status="CAPTURED", amount="700")
        self.assertIn(b"Payment successful", response.content)
        self.order.refresh_from_db()
        self.assertTrue(self.order.paid)
        self.assertEqual(self.order.txId, REAL_TX)
        self.sent.assert_called_once_with(self.order.id)
        self.assertFalse(SecurityIncident.objects.exists())

    def test_confirmed_notification_marks_paid(self):
        with boipa_says(reference=self.ref):
            response = self._notify(reference=self.ref, id=REAL_TX, status="CAPTURED", amount="7.00")
        self.assertEqual(response.status_code, 200)
        self.order.refresh_from_db()
        self.assertTrue(self.order.paid)

    def test_lesson_references_without_a_timestamp_match(self):
        with boipa_says(reference="lesson_5552"):
            self.assertEqual(utils.confirm_payment(REAL_TX, "lesson_5552"), (True, ""))
        with boipa_says(reference="lesson_5553"):
            self.assertFalse(utils.confirm_payment(REAL_TX, "lesson_5552")[0])


class CaptureRaceTests(TestCase):
    """22 Nov 2026 10:59: BOIPA called back before its own record said CAPTURED."""

    def lookups(self, *statuses, reference="lesson_5553"):
        return patch("boipa.utils._fetch_new_api", side_effect=[
            {"captured": s == "CAPTURED", "status": s, "amount": None, "currency": "EUR",
             "raw": {"reference": reference}} for s in statuses])

    def setUp(self):
        sleep = patch("boipa.utils.time.sleep")
        self.sleep = sleep.start()
        self.addCleanup(sleep.stop)

    def test_initiated_then_captured_is_confirmed(self):
        with self.lookups("INITIATED", "INITIATED", "CAPTURED"):
            self.assertEqual(utils.confirm_payment(REAL_TX, "lesson_5553"), (True, ""))
        self.assertEqual(self.sleep.call_count, 2)

    def test_never_captured_gives_up(self):
        with self.lookups(*["INITIATED"] * (len(utils.CAPTURE_WAITS) + 1)):
            ok, reason = utils.confirm_payment(REAL_TX, "lesson_5553")
        self.assertFalse(ok)
        self.assertIn("INITIATED", reason)
        self.assertLessEqual(sum(utils.CAPTURE_WAITS), 12)

    def test_declined_is_not_waited_on(self):
        with self.lookups("DECLINED"):
            self.assertFalse(utils.confirm_payment(REAL_TX, "lesson_5553")[0])
        self.sleep.assert_not_called()

    def test_someone_elses_transaction_is_not_waited_on(self):
        with self.lookups("INITIATED", reference="lesson_1"):
            self.assertFalse(utils.confirm_payment(REAL_TX, "lesson_5553")[0])
        self.sleep.assert_not_called()

    def test_forgery_is_not_waited_on(self):
        with patch("boipa.utils._fetch_new_api", return_value=None):
            self.assertFalse(utils.confirm_payment("TRN_fake", "lesson_5553")[0])
        self.sleep.assert_not_called()


@override_settings(CHATBOT_ABUSE_ALERT_EMAIL="owner@example.com")
class AmountTests(PaymentConfirmationTests.__bases__[0]):
    """22 Nov 2026: the bot asked for payment links at 0.01, -1 and 1E+30."""

    setUp = PaymentConfirmationTests.setUp

    def test_underpayment_is_refused(self):
        with patch("boipa.utils._fetch_new_api", return_value={
                "captured": True, "status": "CAPTURED", "amount": Decimal("0.01"),
                "currency": "EUR", "raw": {"reference": self.ref}}):
            self.client.get(reverse("boipa:payment_response"),
                            {"reference": self.ref, "id": REAL_TX, "status": "CAPTURED"})
        self.order.refresh_from_db()
        self.assertFalse(self.order.paid)

    def test_payment_link_charges_the_order_amount_not_the_url(self):
        with patch("boipa.views.create_hpp_payment_link", return_value={"url": "https://pay.example/x"}) as make:
            for price in ("0.01", "-1", "1E+30", "7.00"):
                self.client.get(reverse("boipa:initiate_payment_session", args=[self.ref, price]))
        self.assertEqual({c.args[2] for c in make.call_args_list}, {Decimal("7.00")})

    def test_no_link_for_a_paid_or_missing_order(self):
        self.order.paid = True
        self.order.save()
        with patch("boipa.views.create_hpp_payment_link") as make:
            self.client.get(reverse("boipa:initiate_payment_session", args=[self.ref, "7.00"]))
            self.client.get(reverse("boipa:initiate_payment_session", args=["swims_99999999_1", "7.00"]))
            make.assert_not_called()
