"""Tests for signup and for swimmer records.

Two things are covered here, both about information a guardian must supply.

The phone number: guardians are contacted by phone about classes, so a signup
path that does not collect one produces an account nobody can reach. The Google
path collected none at all until CustomSocialSignupForm existed.

Medical information: kept in its own field, separate from notes. The pool's rule
is that only medical information goes in front of a teacher at poolside; the
general notes box has years of unrelated content in it, and it is deliberately
left alone rather than migrated or cleared.
"""
import itertools
import time
from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount, SocialLogin
from allauth.socialaccount.views import SignupView
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from users.forms import CustomSignupForm, CustomSocialSignupForm
from users.models import Swimling

User = get_user_model()


def make_sociallogin(email="googler@test.com"):
    return SocialLogin(
        user=User(email=email, first_name="Goo", last_name="Gler"),
        account=SocialAccount(provider="google", uid="123", extra_data={"email": email}),
    )


class GoogleSignupPhoneTests(TestCase):
    def setUp(self):
        self.sociallogin = make_sociallogin()

    def bound(self, phone):
        return CustomSocialSignupForm(
            data={"email": "googler@test.com", "phone_number": phone},
            sociallogin=self.sociallogin,
        )

    def test_allauth_uses_our_form(self):
        """The setting has to be wired, or the stock form silently takes over and
        asks for nothing but an email address."""
        self.assertIs(SignupView().get_form_class(), CustomSocialSignupForm)

    def test_the_form_asks_for_a_phone_number(self):
        form = CustomSocialSignupForm(sociallogin=self.sociallogin)
        self.assertIn("phone_number", form.fields)
        self.assertTrue(form.fields["phone_number"].required)

    def test_signup_without_a_phone_number_is_rejected(self):
        form = self.bound("")
        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)

    def test_a_non_irish_number_is_rejected_with_a_useful_message(self):
        form = self.bound("+442071838750")
        self.assertFalse(form.is_valid())
        self.assertIn("Irish phone number", " ".join(form.errors["phone_number"]))

    def test_a_national_format_irish_number_is_accepted(self):
        form = self.bound("0851639462")
        self.assertTrue(form.is_valid(), form.errors)

    def test_an_e164_irish_number_is_accepted(self):
        form = self.bound("+353851639462")
        self.assertTrue(form.is_valid(), form.errors)

    def test_the_number_is_stored_on_the_user(self):
        """Stored as E.164, and on mobile_phone — the field every class list,
        admin list and school export actually reads."""
        form = self.bound("0851639462")
        self.assertTrue(form.is_valid(), form.errors)

        user = User.objects.create_user(
            email="googler@test.com", password="x", first_name="Goo",
        )
        request = RequestFactory().post("/accounts/social/signup/")

        # Patch allauth's own user creation: this asserts what our mixin does with
        # the user, not how allauth builds one from a sociallogin.
        with patch(
            "allauth.socialaccount.forms.SignupForm.save", return_value=user
        ):
            saved = form.save(request)

        saved.refresh_from_db()
        self.assertEqual(str(saved.mobile_phone), "+353851639462")


class EmailSignupPhoneTests(TestCase):
    """The email path already required a phone; its validation and saving moved to
    the shared mixin, so it is checked here against regression."""

    def bound(self, phone):
        return CustomSignupForm(data={
            "email": "parent@test.com",
            "first_name": "Pat",
            "last_name": "Parent",
            "password1": "swimming-pool-42",
            "password2": "swimming-pool-42",
            "phone_number": phone,
        })

    def test_a_non_irish_number_is_still_rejected(self):
        form = self.bound("+442071838750")
        self.assertFalse(form.is_valid())
        self.assertIn("Irish phone number", " ".join(form.errors["phone_number"]))

    def test_a_missing_number_is_still_rejected(self):
        form = self.bound("")
        self.assertFalse(form.is_valid())
        self.assertIn("phone_number", form.errors)


class MedicalInfoTests(TestCase):
    def setUp(self):
        self.guardian = User.objects.create_user(
            email="guardian@test.com", password="testpass123", first_name="Pat",
        )
        self.swimling = Swimling.objects.create(
            guardian=self.guardian, first_name="Aoife", last_name="Ruane",
            dob="2015-06-15",
            notes="Loves the slide. Dad collects on Tuesdays.",
            medical_info="Asthma - inhaler in bag",
        )

    def test_the_two_boxes_are_independent(self):
        self.swimling.refresh_from_db()
        self.assertEqual(self.swimling.medical_info, "Asthma - inhaler in bag")
        self.assertIn("Loves the slide", self.swimling.notes)

    def test_a_guardian_can_set_medical_info(self):
        self.client.force_login(self.guardian)

        response = self.client.post(
            reverse("swimling_dashboard:edit-swimling", args=[self.swimling.id]),
            {
                "first_name": "Aoife", "last_name": "Ruane", "dob": "2015-06-15",
                "sco_role_num": "", "medical_info": "Peanut allergy - epipen",
                "notes": "Loves the slide. Dad collects on Tuesdays.",
            },
        )
        self.assertIn(response.status_code, (200, 302))

        self.swimling.refresh_from_db()
        self.assertEqual(self.swimling.medical_info, "Peanut allergy - epipen")
        # The notes box must survive a medical edit untouched.
        self.assertIn("Loves the slide", self.swimling.notes)

    def test_a_guardian_only_sees_their_own_child(self):
        other = User.objects.create_user(
            email="other@test.com", password="x", first_name="O",
        )
        self.client.force_login(other)

        response = self.client.get(
            reverse("swimling_dashboard:edit-swimling", args=[self.swimling.id])
        )
        self.assertNotEqual(response.status_code, 200)


class MyBookingsQueryCountTests(TestCase):
    """
    The lesson card shows one line per coupon and reads total_discount, both off
    the coupon_redemptions relation. Left unprefetched that is two queries per
    order — invisible on a test account with one booking, and quietly linear for
    a guardian with years of them.
    """

    def setUp(self):
        from datetime import date, time, timedelta
        from decimal import Decimal

        from coupons.models import Coupon
        from coupons.services import CouponService
        from lessons.models import Category, Product, Program
        from lessons_bookings.models import Term
        from lessons_orders.models import Order, OrderItem
        from users.models import Swimling

        self.user = User.objects.create_user(email="bookings@example.com", password="pw12345!")
        now = timezone.now()
        today = now.date()
        program = Program.objects.create(name="Bookings Prog")
        category = Category.objects.create(
            program=program, name="Bookings Cat", slug="bookings-cat", stage="Stage 1",
        )
        term = Term.objects.create(
            start_date=today + timedelta(days=7), end_date=today + timedelta(days=63),
            rebooking_date=today - timedelta(days=7), booking_date=today - timedelta(days=5),
            assessment_date=today + timedelta(days=64),
        )
        swimling = Swimling.objects.create(
            guardian=self.user, first_name="Kid", last_name="Bookings", dob=date(2016, 1, 1),
        )
        product = Product.objects.create(
            category=category, day_of_week=0, start_time=time(10, 0), end_time=time(10, 45),
            num_places=10, num_weeks=8, price=Decimal("100.00"), active=True,
        )

        counter = itertools.count()

        def make_orders(count):
            for _ in range(count):
                i = next(counter)
                order = Order.objects.create(user=self.user, paid=True, amount=Decimal("60.00"))
                OrderItem.objects.create(
                    order=order, product=product, price=Decimal("100.00"),
                    quantity=1, swimling=swimling, term=term,
                )
                for j in range(2):
                    coupon = Coupon.objects.create(
                        code=f"QC-{i}-{j}", discount_type="fixed",
                        discount_value=Decimal("20.00"), balance_remaining=Decimal("20.00"),
                        valid_from=now - timedelta(days=1), valid_to=now + timedelta(days=30),
                    )
                    CouponService(coupon).apply(
                        purchase_obj=order, amount=Decimal("100.00"),
                        context="lessons", discount_cap=Decimal("100.00"),
                    )

        self.make_orders = make_orders

    def _query_count(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        client = Client()
        client.force_login(self.user)
        # The first page view of the day records the user as active; keep that
        # one-off write out of the count.
        client.get(reverse("users:my_bookings"))
        with CaptureQueriesContext(connection) as ctx:
            response = client.get(reverse("users:my_bookings"))
        self.assertEqual(response.status_code, 200)
        return len(ctx.captured_queries)

    def test_more_orders_do_not_cost_more_queries(self):
        self.make_orders(2)
        for_two = self._query_count()

        self.make_orders(6)
        for_eight = self._query_count()

        self.assertEqual(for_eight, for_two)


class LoginEventTests(TestCase):
    """Each login is recorded, for the activity report's login counts."""

    def test_login_records_an_event(self):
        from users.models import LoginEvent

        user = User.objects.create_user(email="logger@test.com", password="pw", first_name="L")
        self.assertTrue(self.client.login(email="logger@test.com", password="pw"))
        self.assertEqual(LoginEvent.objects.filter(user=user).count(), 1)

    def test_hijack_is_not_counted_as_a_login(self):
        from users.models import LoginEvent

        admin = User.objects.create_superuser(email="boss@test.com", password="pw", first_name="B")
        customer = User.objects.create_user(email="parent@test.com", password="pw", first_name="P")
        self.client.force_login(admin)
        LoginEvent.objects.all().delete()

        response = self.client.post(reverse("hijack:acquire"), {"user_pk": customer.pk})
        self.assertEqual(response.status_code, 302)
        self.client.post(reverse("hijack:release"))
        self.assertFalse(LoginEvent.objects.exists())


class LoginPagePasswordTests(TestCase):
    """The login page must mask the password and never send it back.

    Until 2026-10-19 the template read field.widget.input_type, which is empty
    on a bound field, so every input rendered as type="" (plain text), and a
    failed login echoed the typed password back into the page.
    """

    def test_the_password_box_is_masked(self):
        response = self.client.get(reverse("account_login"))
        self.assertContains(response, 'type="password" name="password"')
        self.assertContains(response, 'type="email" name="login"')

    def test_a_failed_login_does_not_echo_the_password(self):
        response = self.client.post(
            reverse("account_login"), {"login": "nobody@test.com", "password": "S3cret-typed-pw"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "S3cret-typed-pw")
        self.assertContains(response, 'value="nobody@test.com"')


@override_settings(TCSP_MFA_ON=True)
class StaffTwoFactorTests(TestCase):
    """Two-factor authentication: required for staff, optional for everyone else.

    Staff can open every family's records and hijack any account, so a staff
    password alone must not be enough. The failure modes worth guarding are the
    quiet ones: a login route that skips the second factor, and a redirect loop
    that locks staff out of the site entirely.
    """

    def setUp(self):
        self.staff = User.objects.create_superuser(email="staff@test.com", password="pw", first_name="S")

    def enrol(self, user):
        from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret

        TOTP.activate(user, generate_totp_secret())

    def test_staff_without_two_factor_are_sent_to_set_it_up(self):
        self.client.force_login(self.staff)
        response = self.client.get("/finance/")
        self.assertRedirects(response, reverse("mfa_activate_totp"), fetch_redirect_response=False)

    def test_the_setup_page_itself_is_reachable(self):
        """The page they are sent to must not redirect again."""
        # A real sign-in, not force_login: allauth asks for the password again
        # unless it has seen one recently.
        self.client.post(reverse("account_login"), {"login": "staff@test.com", "password": "pw"})
        response = self.client.get(reverse("mfa_activate_totp"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data:image/svg+xml")  # the QR code

    def open_setup_page(self):
        self.client.post(reverse("account_login"), {"login": "staff@test.com", "password": "pw"})
        self.client.get(reverse("mfa_activate_totp"))
        return self.client.session["mfa.totp.secret"]

    def setup_code(self, secret, steps_from_now=0):
        from allauth.mfa.totp.internal.auth import format_hotp_value, hotp_value

        return format_hotp_value(hotp_value(secret, int(time.time()) // 30 + steps_from_now))

    def has_authenticator(self):
        from allauth.mfa.models import Authenticator

        return Authenticator.objects.filter(user=self.staff, type=Authenticator.Type.TOTP).exists()

    def test_reloading_the_setup_page_keeps_the_scanned_code_working(self):
        secret = self.open_setup_page()
        self.client.get(reverse("mfa_activate_totp"))
        self.assertEqual(self.client.session["mfa.totp.secret"], secret)
        self.client.post(reverse("mfa_activate_totp"), {"code": self.setup_code(secret)})
        self.assertTrue(self.has_authenticator())

    def test_a_code_that_has_only_just_changed_is_accepted(self):
        secret = self.open_setup_page()
        self.client.post(reverse("mfa_activate_totp"), {"code": self.setup_code(secret, steps_from_now=-1)})
        self.assertTrue(self.has_authenticator())

    def test_an_old_code_is_still_refused(self):
        secret = self.open_setup_page()
        self.client.post(reverse("mfa_activate_totp"), {"code": self.setup_code(secret, steps_from_now=-3)})
        self.assertFalse(self.has_authenticator())

    def test_unverified_email_is_sent_to_verify_first(self):
        """allauth refuses to activate while an unverified address exists, so
        sending these staff to the setup page would bounce them forever."""
        from allauth.account.models import EmailAddress

        EmailAddress.objects.create(user=self.staff, email=self.staff.email, verified=False, primary=True)
        self.client.force_login(self.staff)
        response = self.client.get("/finance/")
        self.assertRedirects(response, reverse("account_email"), fetch_redirect_response=False)

    def test_the_verify_page_itself_works(self):
        """The page they are sent to must render and let them re-send the link.
        It didn't on 2026-10-18 (a template error), which locked staff out."""
        from allauth.account.models import EmailAddress

        EmailAddress.objects.create(user=self.staff, email=self.staff.email, verified=False, primary=True)
        self.client.force_login(self.staff)
        response = self.client.get(reverse("account_email"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Re-send Verification")

        response = self.client.post(
            reverse("account_email"), {"email": self.staff.email, "action_send": ""}
        )
        self.assertEqual(response.status_code, 302)

    def test_staff_with_two_factor_get_through(self):
        self.enrol(self.staff)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/finance/").status_code, 200)

    def test_customers_are_not_made_to_set_it_up(self):
        User.objects.create_user(email="parent@test.com", password="pw", first_name="P")
        self.client.login(email="parent@test.com", password="pw")
        response = self.client.get(reverse("users:my_bookings"))
        self.assertNotEqual(response.get("Location"), reverse("mfa_activate_totp"))

    def test_hijacked_session_is_not_redirected(self):
        """The person at the keyboard already passed their own second factor."""
        other = User.objects.create_user(email="staff2@test.com", password="pw", first_name="T")
        User.objects.filter(pk=other.pk).update(is_staff=True)
        self.enrol(self.staff)
        self.client.force_login(self.staff)
        self.client.post(reverse("hijack:acquire"), {"user_pk": other.pk})
        response = self.client.get(reverse("users:my_bookings"))
        self.assertNotEqual(response.get("Location"), reverse("mfa_activate_totp"))

    def test_admin_login_form_hands_over_to_allauth(self):
        """The admin's own form checks a password only."""
        for path in ("/admin/login/", "/finance/login/", "/operations/login/", "/settings-admin/login/"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 302, path)
            self.assertTrue(response["Location"].startswith(reverse("account_login")), path)

    def test_password_login_stops_at_the_code_prompt(self):
        self.enrol(self.staff)
        response = self.client.post(reverse("account_login"), {"login": "staff@test.com", "password": "pw"})
        self.assertRedirects(response, reverse("mfa_authenticate"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def sign_in_with_code(self):
        """Password, then the current code; returns the response to the code."""
        from allauth.mfa.models import Authenticator
        from allauth.mfa.totp.internal.auth import (
            format_hotp_value, hotp_value, yield_hotp_counters_from_time,
        )
        from allauth.mfa.utils import decrypt

        self.client.post(reverse("account_login"), {"login": "staff@test.com", "password": "pw"})
        secret = decrypt(Authenticator.objects.get(user=self.staff, type="totp").data["secret"])
        code = format_hotp_value(hotp_value(secret, next(yield_hotp_counters_from_time())))
        return self.client.post(reverse("mfa_authenticate"), {"code": code})

    def test_a_trusted_browser_skips_the_code_for_a_week(self):
        self.enrol(self.staff)
        response = self.sign_in_with_code()
        self.assertRedirects(response, reverse("mfa_trust"), fetch_redirect_response=False)
        page = self.client.get(reverse("mfa_trust"))
        self.assertContains(page, "Trust for 1")  # "Trust for 1 week"

        response = self.client.post(reverse("mfa_trust"), {"action": "trust"})
        self.assertIn("_auth_user_id", self.client.session)
        cookie = response.cookies["mfa_trusted"]
        self.assertEqual(int(cookie["max-age"]), 7 * 24 * 3600)

        self.client.post(reverse("account_logout"))
        response = self.client.post(reverse("account_login"), {"login": "staff@test.com", "password": "pw"})
        self.assertNotEqual(response.get("Location"), reverse("mfa_authenticate"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_not_trusting_asks_for_the_code_next_time(self):
        self.enrol(self.staff)
        self.sign_in_with_code()
        self.client.post(reverse("mfa_trust"), {"action": "skip"})
        self.assertIn("_auth_user_id", self.client.session)

        self.client.post(reverse("account_logout"))
        response = self.client.post(reverse("account_login"), {"login": "staff@test.com", "password": "pw"})
        self.assertRedirects(response, reverse("mfa_authenticate"), fetch_redirect_response=False)

    def test_google_login_stops_at_the_code_prompt(self):
        """The adapter used to throw away perform_login's response and send the
        user to "/" — logged out, with no explanation."""
        from allauth.core import context
        from allauth.core.exceptions import ImmediateHttpResponse
        from django.contrib.auth.models import AnonymousUser
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.sessions.middleware import SessionMiddleware

        from users.adapters import AutoLinkSocialAccountAdapter

        self.enrol(self.staff)
        request = RequestFactory().get("/accounts/google/login/callback/")
        SessionMiddleware(lambda r: None).process_request(request)
        request._messages = FallbackStorage(request)
        request.user = AnonymousUser()

        sociallogin = make_sociallogin(email="staff@test.com")
        # AccountMiddleware sets this context on a real request.
        with context.request_context(request), self.assertRaises(ImmediateHttpResponse) as caught:
            AutoLinkSocialAccountAdapter().pre_social_login(request, sociallogin)
        self.assertEqual(caught.exception.response["Location"], reverse("mfa_authenticate"))

    def test_google_login_counts_as_a_recent_sign_in(self):
        """Otherwise the 2FA setup page asks for a password straight after a
        Google login, and Google-only staff have none to give."""
        from allauth.account.authentication import get_authentication_records
        from allauth.core import context
        from allauth.core.exceptions import ImmediateHttpResponse
        from django.contrib.auth.models import AnonymousUser
        from django.contrib.messages.storage.fallback import FallbackStorage
        from django.contrib.sessions.middleware import SessionMiddleware

        from users.adapters import AutoLinkSocialAccountAdapter

        request = RequestFactory().get("/accounts/google/login/callback/")
        SessionMiddleware(lambda r: None).process_request(request)
        request._messages = FallbackStorage(request)
        request.user = AnonymousUser()

        with context.request_context(request), self.assertRaises(ImmediateHttpResponse):
            AutoLinkSocialAccountAdapter().pre_social_login(request, make_sociallogin(email="staff@test.com"))
        records = get_authentication_records(request)
        self.assertEqual([r["method"] for r in records], ["socialaccount"])

    def test_reset_action_removes_the_authenticator(self):
        from allauth.mfa.models import Authenticator

        customer = User.objects.create_user(email="parent@test.com", password="pw", first_name="P")
        self.enrol(customer)
        self.enrol(self.staff)
        self.client.force_login(self.staff)
        self.client.post(
            reverse("settings:users_user_changelist"),
            {"action": "reset_two_factor", "_selected_action": [customer.pk]},
        )
        self.assertFalse(Authenticator.objects.filter(user=customer).exists())

    def test_only_a_superuser_can_reset_a_staff_account(self):
        from django.contrib.messages.storage.fallback import FallbackStorage

        from allauth.mfa.models import Authenticator
        from custom_admins.usersadmin import reset_two_factor

        manager = User.objects.create_user(email="mgr@test.com", password="pw", first_name="M")
        manager.is_staff = True
        self.enrol(self.staff)
        request = RequestFactory().post("/")
        request.user = manager
        request.session = {}
        request._messages = FallbackStorage(request)
        reset_two_factor(None, request, User.objects.filter(pk=self.staff.pk))
        self.assertTrue(Authenticator.objects.filter(user=self.staff).exists())


@override_settings(TCSP_MFA_ON=False)
class TwoFactorSwitchedOffTests(TestCase):
    """Production until the rollout is agreed: installed, but nobody notices."""

    def setUp(self):
        self.staff = User.objects.create_superuser(email="staff@test.com", password="pw", first_name="S")

    def test_staff_are_not_made_to_set_it_up(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/finance/").status_code, 200)

    def test_admin_login_form_is_the_admin_s_own(self):
        response = self.client.get("/finance/login/")
        self.assertEqual(response.status_code, 200)

    def test_the_menu_does_not_link_to_it(self):
        self.client.force_login(self.staff)
        html = self.client.get(reverse("users:my_bookings")).content.decode()
        self.assertNotIn(reverse("mfa_index"), html)


class LogoutOnAccountPagesTests(TestCase):
    """The navbar's Logout only opens a confirmation box, which has to be on the
    page. Account pages use their own base template, which had none, so Logout
    did nothing there — including on the two-factor setup page."""

    def test_account_pages_carry_the_logout_confirmation(self):
        User.objects.create_user(email="parent@test.com", password="pw", first_name="P")
        self.client.login(email="parent@test.com", password="pw")
        html = self.client.get(reverse("account_change_password")).content.decode()
        self.assertIn("show-logout-modal.window", html)
        self.assertIn(reverse("account_logout"), html)



@override_settings(TCSP_EMAIL_VERIFICATION_FROM=timezone.now() - timezone.timedelta(days=1))
class NewAccountEmailVerificationTests(TestCase):
    """Accounts created from TCSP_EMAIL_VERIFICATION_FROM onwards must confirm
    their email before they can sign in; older accounts, most of which never
    verified, must keep signing in as before."""

    def setUp(self):
        self.user = User.objects.create_user(email="new@test.com", password="pw", first_name="N")

    def sign_in(self):
        return self.client.post(reverse("account_login"), {"login": "new@test.com", "password": "pw"})

    def test_new_unverified_account_is_stopped_and_sent_a_link(self):
        from django.core import mail

        response = self.sign_in()
        self.assertRedirects(response, reverse("account_email_verification_sent"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual([m.to for m in mail.outbox], [["new@test.com"]])
        # The page it lands on must render: a broken account page locked staff
        # out on 2026-10-18.
        self.assertEqual(self.client.get(response.url).status_code, 200)

    def test_following_the_link_finishes_signing_in(self):
        from allauth.account.models import EmailAddress, EmailConfirmationHMAC

        self.sign_in()
        confirmation = EmailConfirmationHMAC(EmailAddress.objects.get(email="new@test.com"))
        url = reverse("account_confirm_email", args=[confirmation.key])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(url)
        self.assertTrue(EmailAddress.objects.get(email="new@test.com").verified)
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_new_verified_account_signs_in(self):
        from allauth.account.models import EmailAddress

        EmailAddress.objects.create(user=self.user, email=self.user.email, verified=True, primary=True)
        self.sign_in()
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    def test_older_unverified_account_still_signs_in(self):
        User.objects.filter(pk=self.user.pk).update(date_joined=timezone.now() - timezone.timedelta(days=30))
        self.sign_in()
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))

    @override_settings(TCSP_EMAIL_VERIFICATION_FROM=None)
    def test_the_requirement_can_be_switched_off(self):
        self.sign_in()
        self.assertEqual(self.client.session["_auth_user_id"], str(self.user.pk))


class EmailConfirmationReminderTests(TestCase):
    """Older customers who never confirmed their email are asked to, on every
    page, but never stopped from booking (Esther, 2026-10-27)."""

    def setUp(self):
        self.user = User.objects.create_user(email="old@test.com", password="pw", first_name="O")
        self.client.force_login(self.user)

    def test_unconfirmed_customer_sees_the_reminder(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Please confirm your email address")
        self.assertContains(response, reverse("users:send_confirmation_email"))

    def test_confirmed_customer_does_not(self):
        from allauth.account.models import EmailAddress

        EmailAddress.objects.create(user=self.user, email="OLD@test.com", verified=True, primary=True)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Please confirm your email address")

    def google(self, **extra_data):
        SocialAccount.objects.create(user=self.user, provider="google", uid="g1", extra_data=extra_data)

    def test_google_verified_address_counts_as_confirmed_and_is_recorded(self):
        from allauth.account.models import EmailAddress

        self.google(email="Old@test.com", email_verified=True)
        self.assertNotContains(self.client.get(reverse("home")), "Please confirm your email address")
        self.assertTrue(EmailAddress.objects.get(user=self.user).verified)

    def test_google_with_an_unverified_record_marks_it_verified(self):
        from allauth.account.models import EmailAddress

        EmailAddress.objects.create(user=self.user, email="old@test.com", verified=False, primary=True)
        self.google(email="old@test.com", verified_email=True)
        self.assertNotContains(self.client.get(reverse("home")), "Please confirm your email address")
        self.assertTrue(EmailAddress.objects.get(user=self.user).verified)

    def test_google_for_a_different_address_does_not_count(self):
        self.google(email="other@gmail.com", email_verified=True)
        self.assertContains(self.client.get(reverse("home")), "Please confirm your email address")

    def test_google_not_verified_does_not_count(self):
        self.google(email="old@test.com", email_verified=False)
        self.assertContains(self.client.get(reverse("home")), "Please confirm your email address")

    def test_not_shown_while_staff_hijack_a_customer(self):
        session = self.client.session
        session["hijack_history"] = ["1"]
        session.save()
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, "Please confirm your email address")

    def test_not_shown_when_signed_out(self):
        self.client.logout()
        self.assertNotContains(self.client.get(reverse("home")), "Please confirm your email address")

    def test_button_sends_the_link_and_returns_to_the_page(self):
        from allauth.account.models import EmailAddress, EmailConfirmationHMAC
        from django.core import mail

        response = self.client.post(reverse("users:send_confirmation_email"), {"next": "/users/profile/"})
        self.assertRedirects(response, "/users/profile/", fetch_redirect_response=False)
        self.assertEqual([m.to for m in mail.outbox], [["old@test.com"]])
        self.assertContains(self.client.get(reverse("home")), "sent a link to")

        # Following the link confirms it, and the reminder goes away.
        confirmation = EmailConfirmationHMAC(EmailAddress.objects.get(email="old@test.com"))
        self.client.post(reverse("account_confirm_email", args=[confirmation.key]))
        self.assertTrue(EmailAddress.objects.get(email="old@test.com").verified)
        self.assertNotContains(self.client.get(reverse("home")), "sent a link to")

    def test_pressing_again_straight_away_does_not_send_a_second(self):
        from django.core import mail

        self.client.post(reverse("users:send_confirmation_email"))
        response = self.client.post(reverse("users:send_confirmation_email"), follow=True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertContains(response, "We sent you an email a few minutes ago")

    def test_next_cannot_send_them_off_site(self):
        response = self.client.post(reverse("users:send_confirmation_email"), {"next": "https://evil.example/"})
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_get_is_refused(self):
        self.assertEqual(self.client.get(reverse("users:send_confirmation_email")).status_code, 405)

    def test_link_survives_mail_clients_that_drop_gradients(self):
        from django.core import mail

        self.client.post(reverse("users:send_confirmation_email"))
        html = dict((t, c) for c, t in mail.outbox[0].alternatives)["text/html"]
        self.assertIn('bgcolor="#2563eb"', html)
        self.assertIn("background-color:#2563eb; color:#ffffff", html)
        self.assertIn("Or paste this link into your browser", html)
        self.assertNotIn("cta-button", html)
