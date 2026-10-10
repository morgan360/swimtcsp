import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from anseo.models import AttendanceEntry
from lessons.models import Category, Product, Program
from lessons_bookings.models import LessonEnrollment, Term
from users.models import Swimling

User = get_user_model()


class TakeRollTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = User.objects.create_user(email="instructor@tcsp.ie", password="pw", first_name="I")
        today = timezone.localdate()
        cls.term = Term.objects.create(start_date=today - timedelta(days=5), end_date=today + timedelta(days=60))
        category = Category.objects.create(name="Beginners 2", program=Program.objects.create(name="P"))
        cls.lesson = Product.objects.create(category=category, day_of_week=5, num_places=6, active=True)
        guardian = User.objects.create_user(email="parent@example.com", password="pw", first_name="P")
        cls.enrolments = [
            LessonEnrollment.objects.create(
                lesson=cls.lesson, term=cls.term,
                swimling=Swimling.objects.create(guardian=guardian, first_name=f"Kid{i}", last_name="T"),
            )
            for i in range(2)
        ]
        cls.url = reverse("anseo:take_roll", args=[cls.lesson.id, cls.term.id])

    def setUp(self):
        self.client.force_login(self.instructor)

    def test_each_swimling_has_one_set_of_inputs(self):
        # Two copies of a radio share one group, so "Mark all" ticked the hidden copy
        # and cleared the visible one; two note boxes submitted the hidden note.
        html = self.client.get(self.url).content.decode()
        for e in self.enrolments:
            self.assertEqual(len(re.findall(rf'name="status_{e.id}"\s+value="present"', html)), 1)
            self.assertEqual(html.count(f'name="note_{e.id}"'), 1)

    def test_saves_status_and_note(self):
        e = self.enrolments[0]
        self.client.post(self.url, {f"status_{e.id}": "present", f"note_{e.id}": "Goggles lost"})
        entry = AttendanceEntry.objects.get(enrollment=e)
        self.assertEqual((entry.status, entry.note), ("present", "Goggles lost"))
