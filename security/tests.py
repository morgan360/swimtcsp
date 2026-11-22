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
    def test_scanner_is_blocked_once_without_an_email(self):
        for _ in range(PROBE_LIMIT):
            self.assertEqual(self.client.get("/wp-login.php").status_code, 404)
        self.assertEqual(self.client.get("/").status_code, 403)
        self.assertEqual(self.client.get("/wp-login.php").status_code, 403)
        self.assertEqual(SecurityIncident.objects.filter(kind="probe_blocked").count(), 1)
        self.assertEqual(mail.outbox, [])

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


class CsrfBlockTests(SecurityTestCase):
    def test_burst_of_forged_posts_is_blocked(self):
        client = self.client_class(enforce_csrf_checks=True)
        for _ in range(CSRF_LIMIT):
            self.assertEqual(client.post("/accounts/login/").status_code, 403)
        self.assertEqual(SecurityIncident.objects.filter(kind="csrf_blocked").count(), 1)
        self.assertEqual(client.get("/").status_code, 403)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("blocked", mail.outbox[0].body)

    def test_emails_are_capped(self):
        client = self.client_class(enforce_csrf_checks=True)
        with patch("security.services.EMAILS_PER_HOUR", 1):
            for n in range(1, 4):
                for _ in range(CSRF_LIMIT):
                    client.post("/accounts/login/", HTTP_X_REAL_IP=f"10.0.1.{n}")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(SecurityIncident.objects.filter(kind="csrf_blocked").count(), 3)


class ConfigProbeTests(SecurityTestCase):
    def test_one_request_for_a_secrets_file_blocks(self):
        for path in ("/.env", "/.git/config", "/settings.py", "/local_settings.py", "/phpinfo.php", "/server-status"):
            cache.clear()
            self.assertEqual(self.client.get(path).status_code, 404, path)
            self.assertEqual(self.client.get("/").status_code, 403, path)

    def test_wordpress_paths_still_need_several(self):
        # Old /wp-content/ image links from the previous site are still followed by real people.
        self.client.get("/wp-content/uploads/2020/09/logo.png")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_a_missing_download_does_not_block(self):
        self.client.get("/media/timetable-2025.zip")
        self.assertEqual(self.client.get("/").status_code, 200)


class ScriptedClientTests(SecurityTestCase):
    def test_command_line_tools_are_turned_away(self):
        for agent in ("curl/7.88.1", "Go-http-client/1.1", "python-requests/2.31.0",
                      "Python/3.11 aiohttp/3.9.1", "Wget/1.21", "sqlmap/1.7"):
            self.assertEqual(self.client.get("/", HTTP_USER_AGENT=agent).status_code, 403, agent)

    def test_browsers_and_link_previews_get_through(self):
        for agent in ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15",
                      "facebookexternalhit/1.1", "Googlebot/2.1", "HostedPaymentPage", ""):
            self.assertEqual(self.client.get("/", HTTP_USER_AGENT=agent).status_code, 200, agent)

    def test_payment_callback_is_exempt(self):
        response = self.client.post("/boipa/payment-notification/", HTTP_USER_AGENT="curl/7.88.1")
        self.assertNotEqual(response.status_code, 403)

    def test_a_scan_is_one_row_not_one_per_request(self):
        for _ in range(10):
            self.client.get("/", HTTP_USER_AGENT="curl/7.88.1")
        self.assertEqual(SecurityIncident.objects.filter(kind="script_refused").count(), 1)
        self.assertEqual(mail.outbox, [])

    @override_settings(SECURITY_BLOCKING_ON=False)
    def test_switch_lets_scripts_through(self):
        self.assertEqual(self.client.get("/", HTTP_USER_AGENT="curl/7.88.1").status_code, 200)
