"""
Guardrails on the cart's coupon panel.

These are the rules a customer meets directly — how many coupons they may
stack, which kinds combine, and what the panel tells them when one is refused.
"""
from datetime import date, time, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from coupons.models import Coupon
from coupons.services import MAX_COUPONS_PER_ORDER
from lessons.models import Category, Product, Program
from lessons_bookings.models import Term
from users.models import Swimling

User = get_user_model()


class CartCouponPanelTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(email="panel@example.com", password="pw12345!")
        self.client.force_login(self.user)

        self.now = timezone.now()
        today = self.now.date()
        self.program = Program.objects.create(name="Panel Prog")
        self.category = Category.objects.create(
            program=self.program, name="Panel Cat", slug="panel-cat", stage="Stage 1",
        )
        # Booking open, term not yet started, so the cart charges the full
        # €100 term price rather than a weekday-dependent prorated one.
        self.term = Term.objects.create(
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=63),
            rebooking_date=today - timedelta(days=7),
            booking_date=today - timedelta(days=5),
            assessment_date=today + timedelta(days=64),
        )
        self.swimling = Swimling.objects.create(
            guardian=self.user, first_name="Kid", last_name="Panel", dob=date(2016, 1, 1),
        )
        self.product = Product.objects.create(
            category=self.category, day_of_week=0,
            start_time=time(10, 0), end_time=time(10, 45),
            num_places=10, num_weeks=8, price=Decimal("100.00"), active=True,
        )
        self._seed_cart()

    def _seed_cart(self):
        from shopping_cart.cart import Cart

        request = type("R", (), {})()
        request.session = self.client.session
        cart = Cart(request)
        cart.add(product=self.product, type="lesson",
                 swimling_id=self.swimling.id, term=self.term)
        request.session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = request.session.session_key

    def _make_coupon(self, code, value="20.00", discount_type="fixed", **kwargs):
        opts = dict(
            code=code, discount_type=discount_type, discount_value=Decimal(value),
            balance_remaining=Decimal(value),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=30),
        )
        opts.update(kwargs)
        return Coupon.objects.create(**opts)

    def _apply(self, code):
        return self.client.post(reverse("shopping_cart:validate_coupon"), {"code": code})

    def _applied_codes(self):
        return self.client.session.get("coupon_codes", [])

    def test_a_second_fixed_coupon_stacks_and_the_panel_shows_both(self):
        self._make_coupon("PANEL-A", "20.00")
        self._make_coupon("PANEL-B", "15.00")

        self._apply("PANEL-A")
        response = self._apply("PANEL-B")

        self.assertEqual(self._applied_codes(), ["PANEL-A", "PANEL-B"])
        self.assertContains(response, "PANEL-A")
        self.assertContains(response, "PANEL-B")
        # Subtotal 100 − 20 − 15.
        self.assertContains(response, "65.00")

    def test_the_same_coupon_cannot_be_applied_twice(self):
        self._make_coupon("DOUBLE-UP", "20.00")

        self._apply("DOUBLE-UP")
        response = self._apply("DOUBLE-UP")

        self.assertContains(response, "already applied")
        self.assertEqual(self._applied_codes(), ["DOUBLE-UP"])

    def test_no_more_than_the_maximum_may_be_applied(self):
        for i in range(MAX_COUPONS_PER_ORDER + 1):
            self._make_coupon(f"MANY-{i}", "5.00")
            response = self._apply(f"MANY-{i}")

        self.assertContains(response, "at most")
        self.assertEqual(len(self._applied_codes()), MAX_COUPONS_PER_ORDER)

    def test_a_percentage_coupon_will_not_combine_with_a_fixed_one(self):
        self._make_coupon("FIXED-ONE", "20.00")
        self._make_coupon("PERCENT-ONE", "10.00", discount_type="percent")

        self._apply("FIXED-ONE")
        response = self._apply("PERCENT-ONE")

        self.assertContains(response, "Only fixed-amount coupons can be combined")
        self.assertEqual(self._applied_codes(), ["FIXED-ONE"])

    def test_a_fixed_coupon_will_not_join_a_percentage_one(self):
        """The rule has to hold whichever kind was applied first."""
        self._make_coupon("PC-FIRST", "10.00", discount_type="percent")
        self._make_coupon("FX-SECOND", "20.00")

        self._apply("PC-FIRST")
        response = self._apply("FX-SECOND")

        self.assertContains(response, "Only fixed-amount coupons can be combined")
        self.assertEqual(self._applied_codes(), ["PC-FIRST"])

    def test_a_percentage_coupon_is_still_fine_on_its_own(self):
        self._make_coupon("PC-ALONE", "10.00", discount_type="percent")

        response = self._apply("PC-ALONE")

        self.assertEqual(self._applied_codes(), ["PC-ALONE"])
        self.assertContains(response, "90.00")

    def test_an_unknown_code_is_refused_without_disturbing_the_applied_one(self):
        self._make_coupon("KEEP-ME", "20.00")

        self._apply("KEEP-ME")
        response = self._apply("NOT-A-CODE")

        self.assertContains(response, "Invalid coupon code")
        self.assertEqual(self._applied_codes(), ["KEEP-ME"])
        self.assertContains(response, "80.00")

    def test_removing_one_coupon_leaves_the_other_applied(self):
        self._make_coupon("GO-AWAY", "20.00")
        self._make_coupon("STAY-PUT", "15.00")
        self._apply("GO-AWAY")
        self._apply("STAY-PUT")

        response = self.client.post(
            reverse("shopping_cart:remove_coupon_code", kwargs={"code": "GO-AWAY"}),
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(self._applied_codes(), ["STAY-PUT"])
        self.assertContains(response, "85.00")

    def test_the_cart_page_shows_the_stacked_total(self):
        self._make_coupon("CART-A", "20.00")
        self._make_coupon("CART-B", "15.00")
        self._apply("CART-A")
        self._apply("CART-B")

        response = self.client.get(reverse("shopping_cart:cart_detail"))

        self.assertContains(response, "65.00")

    def test_a_coupon_that_lapses_is_dropped_from_the_cart_page(self):
        """The cart must not keep quoting a discount the coupon no longer gives."""
        coupon = self._make_coupon("LAPSED", "20.00")
        self._apply("LAPSED")
        self.assertEqual(self._applied_codes(), ["LAPSED"])

        coupon.valid_to = self.now - timedelta(hours=1)
        coupon.save()

        response = self.client.get(reverse("shopping_cart:cart_detail"))

        self.assertEqual(self._applied_codes(), [])
        self.assertContains(response, "100.00")


class BookingPauseGateTests(TestCase):
    """The pause has to hold at the endpoints, not just in the buttons.

    A guardian who kept a tab open, bookmarked a lesson, or left items in the
    cart before the pause started can reach these POST endpoints directly, so
    each one refuses on its own rather than trusting the template.
    """
    def setUp(self):
        self.client = Client()
        self.guardian = User.objects.create_user(email="paused@example.com", password="pw12345!")
        self.staff = User.objects.create_user(email="staff@example.com", password="pw12345!")
        self.staff.is_staff = True
        self.staff.save(update_fields=['is_staff'])

        today = timezone.now().date()
        self.program = Program.objects.create(name="Pause Prog")
        self.category = Category.objects.create(
            program=self.program, name="Pause Cat", slug="pause-cat", stage="Stage 1",
        )
        # Rebooking opened a week ago, the pause started yesterday, booking
        # reopens in five days.
        self.term = Term.objects.create(
            start_date=today - timedelta(days=10),
            end_date=today + timedelta(days=30),
            rebooking_date=today - timedelta(days=7),
            pause_date=today - timedelta(days=1),
            booking_date=today + timedelta(days=5),
        )
        self.product = Product.objects.create(
            category=self.category, day_of_week=0,
            start_time=time(10, 0), end_time=time(10, 45),
            num_places=10, num_weeks=8, price=Decimal("100.00"), active=True,
        )
        self.swimling = Swimling.objects.create(
            guardian=self.guardian, first_name="Kid", last_name="Paused",
            dob=date(2016, 1, 1),
        )

    def add_url(self):
        return reverse('shopping_cart:cart_add', args=[self.product.id, 'lesson'])

    def test_the_public_cannot_add_a_lesson_to_the_cart(self):
        self.client.force_login(self.guardian)
        response = self.client.post(self.add_url(), {'swimling': self.swimling.id})

        # fetch_redirect_response=False: the dashboard bounces again for a user
        # who is not yet in the guardian group, which is not what is under test.
        self.assertRedirects(
            response, reverse('swimling_dashboard:guardian_dashboard'),
            fetch_redirect_response=False,
        )
        self.assertNotIn('cart', self.client.session)

    def test_staff_can_still_add_a_lesson_to_the_cart(self):
        """Esther's requirement: staff keep booking swimlings into classes."""
        staff_swimling = Swimling.objects.create(
            guardian=self.staff, first_name="Kid", last_name="Staff",
            dob=date(2016, 1, 1),
        )
        self.client.force_login(self.staff)
        response = self.client.post(self.add_url(), {'swimling': staff_swimling.id})

        self.assertRedirects(response, reverse('shopping_cart:cart_detail'))
        self.assertTrue(self.client.session.get('cart'))

    def test_the_public_cannot_check_out_a_cart_filled_before_the_pause(self):
        self.client.force_login(self.guardian)
        session = self.client.session
        session['cart'] = {
            f'lesson_{self.product.id}_{self.swimling.id}': {
                'price': '100.00', 'quantity': 1,
            }
        }
        session[f'{settings.CART_SESSION_ID}_type'] = 'lesson'
        session.save()

        response = self.client.post(reverse('shopping_cart:payment_process'))

        self.assertRedirects(response, reverse('shopping_cart:cart_detail'))
        # Their selection is still there to pay for once booking reopens.
        self.assertTrue(self.client.session['cart'])

    def test_the_public_cannot_reach_the_rebooking_page(self):
        self.client.force_login(self.guardian)
        response = self.client.get(reverse('shopping_cart:rebooking_page'))
        self.assertRedirects(
            response, reverse('swimling_dashboard:guardian_dashboard'),
            fetch_redirect_response=False,
        )

    def test_a_term_without_a_pause_date_still_books_normally(self):
        """The pause is opt-in; terms that do not set one are untouched."""
        self.term.pause_date = None
        self.term.save()
        self.client.force_login(self.guardian)

        response = self.client.post(self.add_url(), {'swimling': self.swimling.id})

        self.assertRedirects(response, reverse('shopping_cart:cart_detail'))
        self.assertTrue(self.client.session.get('cart'))
