"""Tests for the signup forms, focused on the phone number.

Guardians are contacted by phone about classes, so a signup path that does not
collect one produces an account nobody can reach. The Google path collected none
at all until CustomSocialSignupForm existed.
"""
from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount, SocialLogin
from allauth.socialaccount.views import SignupView
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from users.forms import CustomSignupForm, CustomSocialSignupForm

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
