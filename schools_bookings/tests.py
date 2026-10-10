from datetime import time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from schools.models import ScoCategory, ScoLessons, ScoProgram, ScoSchool
from schools_bookings.models import ScoEnrollment, ScoTerm
from schools_orders.models import Order, OrderItem
from users.models import Swimling

User = get_user_model()


class SchoolClassCapacityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.parent = User.objects.create_user(email="parent@example.com", password="pw", first_name="P")
        cls.school = ScoSchool.objects.create(name="Zion", sco_role_num="14917J")
        today = timezone.localdate()
        def term(start, active):
            return ScoTerm.objects.create(
                school=cls.school, start_date=start, end_date=start + timedelta(days=90),
                booking_start_date=start - timedelta(days=14), booking_end_date=start + timedelta(days=7),
                assessment_date=start + timedelta(days=91), is_active=active,
            )
        cls.term = term(today, True)
        cls.old_term = term(today - timedelta(days=200), False)
        category = ScoCategory.objects.create(
            program=ScoProgram.objects.create(name="Schools"), name="Improvers 1", slug="improvers-1",
        )
        cls.small = ScoLessons.objects.create(
            category=category, school=cls.school, day_of_week=4, start_time=time(14, 20),
            end_time=time(14, 50), num_places=2, num_weeks=8, price=Decimal("64.00"), active=True,
        )
        cls.roomy = ScoLessons.objects.create(
            category=category, school=cls.school, day_of_week=3, start_time=time(14, 20),
            end_time=time(14, 50), num_places=13, num_weeks=8, price=Decimal("64.00"), active=True,
        )
        cls.swimling = Swimling.objects.create(
            guardian=cls.parent, first_name="New", last_name="Kid", sco_role_num=cls.school.sco_role_num,
        )
        cls.url = reverse("schools_bookings:book_lesson", args=[cls.swimling.id, cls.term.id])

    def setUp(self):
        self.client.force_login(self.parent)

    def enrol(self, lesson, term, n):
        for i in range(n):
            kid = Swimling.objects.create(guardian=self.parent, first_name=f"K{i}", last_name="T")
            ScoEnrollment.objects.create(lesson=lesson, swimling=kid, term=term)

    def fill_small_class(self):
        self.enrol(self.small, self.term, 2)

    def test_places_left_counts_only_that_term(self):
        self.enrol(self.small, self.old_term, 2)
        self.enrol(self.small, self.term, 1)
        self.assertEqual(self.small.places_left_in(self.term), 1)
        self.assertFalse(self.small.is_full_in(self.term))
        self.enrol(self.small, self.term, 1)
        self.assertTrue(self.small.is_full_in(self.term))

    def test_booking_page_shows_places_left_and_full(self):
        self.fill_small_class()
        self.enrol(self.roomy, self.term, 4)
        # Parents reach the page from their dashboard; the form posts to book_lesson.
        dashboard_url = reverse("swimling_dashboard:school_checkout", args=[self.swimling.id, self.term.id])
        for url in (dashboard_url, self.url):
            html = self.client.get(url).content.decode()
            self.assertIn("9 of 13 left", html)
            self.assertIn("Full", html)

    @patch("schools_bookings.views.initiate_boipa_payment_session", return_value=HttpResponse("to BOIPA"))
    def test_full_class_is_refused_before_payment(self, pay):
        self.fill_small_class()
        response = self.client.post(self.url, {"lesson": self.small.id})
        self.assertContains(response, "is full this term")
        pay.assert_not_called()
        self.assertFalse(Order.objects.exists())

    @patch("schools_bookings.views.initiate_boipa_payment_session", return_value=HttpResponse("to BOIPA"))
    def test_class_with_space_goes_to_payment(self, pay):
        self.fill_small_class()
        response = self.client.post(self.url, {"lesson": self.roomy.id})
        self.assertEqual(response.content, b"to BOIPA")
        self.assertEqual(OrderItem.objects.get().product, self.roomy)

    def test_cart_checkout_refuses_full_class(self):
        from shopping_cart.views import process_order_items
        self.fill_small_class()
        cart = SimpleNamespace(cart={"k": {"product_id": self.small.id, "swimling_id": self.swimling.id, "price": "64.00"}})
        order = Order.objects.create(user=self.parent)
        with self.assertRaisesMessage(ValueError, "is full this term"):
            process_order_items(cart, OrderItem, order, ScoLessons, lambda: self.term)
        self.assertFalse(OrderItem.objects.exists())
