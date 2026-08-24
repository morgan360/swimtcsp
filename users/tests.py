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
from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount, SocialLogin
from allauth.socialaccount.views import SignupView
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
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
