from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

import core.urls  # noqa: F401  — registers the panels' models
from lessons.models import Category, Product, Program
from lessons_bookings.models import LessonEnrollment, Term
from users.models import Swimling

User = get_user_model()


class LessonEnrollmentsReportTests(TestCase):
    """The finance panel's enrollments-per-term and fill-per-lesson page."""

    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user(email="manager@tcsp.ie", password="pw", first_name="M")
        cls.manager.is_staff = True
        cls.manager.save(update_fields=["is_staff"])
        cls.manager.groups.add(Group.objects.get_or_create(name="Manager")[0])

        today = timezone.now().date()
        cls.last = Term.objects.create(start_date=today - timedelta(days=100), end_date=today - timedelta(days=30))
        cls.this = Term.objects.create(start_date=today - timedelta(days=10), end_date=today + timedelta(days=50))
        # A term older than "last" must not appear.
        Term.objects.create(start_date=today - timedelta(days=300), end_date=today - timedelta(days=200))

        category = Category.objects.create(name="Beginners 1", program=Program.objects.create(name="P"))
        cls.active = Product.objects.create(category=category, day_of_week=0, num_places=4, active=True)
        cls.retired = Product.objects.create(category=category, day_of_week=2, num_places=10, active=False)
        Product.objects.create(category=category, day_of_week=4, num_places=8, active=False)  # never used

        guardian = User.objects.create_user(email="parent@example.com", password="pw", first_name="P")
        kids = [Swimling.objects.create(guardian=guardian, first_name=f"Kid{i}", last_name="T") for i in range(5)]
        for kid in kids[:3]:
            LessonEnrollment.objects.create(lesson=cls.active, swimling=kid, term=cls.this)
        LessonEnrollment.objects.create(lesson=cls.active, swimling=kids[0], term=cls.last)
        LessonEnrollment.objects.create(lesson=cls.retired, swimling=kids[4], term=cls.last)

    def get(self):
        self.client.force_login(self.manager)
        return self.client.get(reverse("finance:lesson_enrollments"))

    def test_index_links_to_the_report(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("finance:index"))
        self.assertContains(response, reverse("finance:lesson_enrollments"))

    def test_shows_only_the_terms_that_exist(self):
        response = self.get()
        self.assertEqual(response.status_code, 200)
        summaries = response.context["term_summaries"]
        # No next term has been created, so only last and this.
        self.assertEqual([s["label"] for s in summaries], ["Last term", "This term"])
        self.assertEqual([s["term"] for s in summaries], [self.last, self.this])

    def test_term_totals(self):
        last, this = self.get().context["term_summaries"]
        # Last term: the active lesson (1/4) and the retired one that had a swimmer (1/10).
        self.assertEqual((last["enrolled"], last["places"]), (2, 14))
        # This term: only the active lesson is running.
        self.assertEqual((this["enrolled"], this["places"], this["pct"]), (3, 4, 75))

    def test_lesson_fill(self):
        rows = {row["lesson"]: row for row in self.get().context["rows"]}
        # The retired lesson with no swimmers in any shown term is left out.
        self.assertEqual(set(rows), {self.active, self.retired})
        self.assertEqual([c["pct"] for c in rows[self.active]["cells"]], [25, 75])
        last_cell, this_cell = rows[self.retired]["cells"]
        self.assertEqual(last_cell["pct"], 10)
        self.assertFalse(this_cell["running"])
