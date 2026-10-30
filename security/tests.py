from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings

from security.models import SecurityIncident
from security.services import CSRF_LIMIT, PROBE_LIMIT


@override_settings(CHATBOT_ABUSE_ALERT_EMAIL="owner@example.com")
class SecurityTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)


class ScannerBlockTests(SecurityTestCase):
    def test_scanner_is_blocked_once_with_one_email(self):
        for _ in range(PROBE_LIMIT):
            self.assertEqual(self.client.get("/wp-login.php").status_code, 404)
        self.assertEqual(self.client.get("/").status_code, 403)
        self.assertEqual(self.client.get("/wp-login.php").status_code, 403)
        self.assertEqual(SecurityIncident.objects.filter(kind="probe_blocked").count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("blocked", mail.outbox[0].body)

    def test_ordinary_404s_do_not_count(self):
        for _ in range(PROBE_LIMIT * 3):
            self.client.get("/favicon-nope.ico")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_one_blocked_address_leaves_others_alone(self):
        for _ in range(PROBE_LIMIT):
            self.client.get("/.env", REMOTE_ADDR="10.0.0.1", HTTP_X_REAL_IP="10.0.0.1")
        self.assertEqual(self.client.get("/", HTTP_X_REAL_IP="10.0.0.1").status_code, 403)
        self.assertEqual(self.client.get("/", HTTP_X_REAL_IP="10.0.0.2").status_code, 200)

    def test_payment_callback_gets_through_a_block(self):
        for _ in range(PROBE_LIMIT):
            self.client.get("/wp-login.php")
        self.assertNotEqual(self.client.post("/boipa/payment-notification/").status_code, 403)

    def test_cache_failure_lets_requests_through(self):
        with patch("security.services.cache.get", side_effect=RuntimeError("db down")):
            self.assertEqual(self.client.get("/").status_code, 200)

    @override_settings(SECURITY_BLOCKING_ON=False)
    def test_switch_turns_blocking_off(self):
        for _ in range(PROBE_LIMIT):
            self.client.get("/wp-login.php")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_emails_are_capped(self):
        with patch("security.services.EMAILS_PER_HOUR", 1):
            for n in range(1, 4):
                for _ in range(PROBE_LIMIT):
                    self.client.get("/wp-login.php", HTTP_X_REAL_IP=f"10.0.1.{n}")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(SecurityIncident.objects.filter(kind="probe_blocked").count(), 3)


class CsrfBlockTests(SecurityTestCase):
    def test_burst_of_forged_posts_is_blocked(self):
        client = self.client_class(enforce_csrf_checks=True)
        for _ in range(CSRF_LIMIT):
            self.assertEqual(client.post("/accounts/login/").status_code, 403)
        self.assertEqual(SecurityIncident.objects.filter(kind="csrf_blocked").count(), 1)
        self.assertEqual(client.get("/").status_code, 403)
