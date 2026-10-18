"""Tests for a guardian joining the waiting list from their dashboard.

The first choice becomes the entry's product. A form sent without one used to
reach the model's duplicate check with no product and crash with a 500, as
happened on production on 2026-10-18.
"""
from datetime import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from lessons.models import Category, Product, Program
from users.models import Swimling
from waiting_list.models import WaitingList

User = get_user_model()


class JoinWaitingListTests(TestCase):
    def setUp(self):
        self.guardian = User.objects.create_user(email="guardian@test.com", password="pw12345!")
        self.swimling = Swimling.objects.create(
            guardian=self.guardian, first_name="Kid", last_name="Waiting", dob="2016-01-01",
        )
        program = Program.objects.create(name="WL Prog")
        category = Category.objects.create(
            program=program, name="WL Cat", slug="wl-cat", stage="Stage 1",
        )
        self.product = Product.objects.create(
            category=category, day_of_week=2, start_time=time(19, 0), end_time=time(19, 30),
            num_places=10, num_weeks=8, price=Decimal("100.00"), active=True,
        )
        self.url = reverse("waiting_list:join_waiting_list", args=[self.swimling.id])
        self.client.force_login(self.guardian)

    def post(self, **fields):
        data = {"is_transfer_request": "False", "notes": ""}
        data.update(fields)
        return self.client.post(self.url, data)

    def test_joining_with_a_first_choice_creates_the_entry(self):
        response = self.post(preferred_lesson_1=self.product.id)

        self.assertEqual(response.status_code, 302)
        entry = WaitingList.objects.get(swimling=self.swimling)
        self.assertEqual(entry.product, self.product)

    def test_no_first_choice_shows_an_error_instead_of_crashing(self):
        response = self.post(preferred_lesson_2=self.product.id)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["preferred_lesson_1"])
        self.assertFalse(WaitingList.objects.exists())

    def test_joining_twice_for_the_same_lesson_says_so(self):
        self.post(preferred_lesson_1=self.product.id)
        response = self.post(preferred_lesson_1=self.product.id)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already on the waiting list")
        self.assertEqual(WaitingList.objects.count(), 1)
