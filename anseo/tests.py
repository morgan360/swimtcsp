import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
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
        cls.instructor.groups.add(Group.objects.create(name="instructor"))
        today = timezone.localdate()
        cls.term = Term.objects.create(start_date=today - timedelta(days=5), end_date=today + timedelta(days=60))
        category = Category.objects.create(name="Beginners 2", program=Program.objects.create(name="P"))
        cls.lesson = Product.objects.create(category=category, day_of_week=5, num_places=6, active=True)
        cls.guardian = guardian = User.objects.create_user(email="parent@example.com", password="pw", first_name="P")
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

    def test_parents_cannot_read_or_change_registers(self):
        self.client.force_login(self.guardian)
        e = self.enrolments[0]
        history = reverse("anseo:attendance_history", args=[self.lesson.id, self.term.id])
        matrix = reverse("anseo:attendance_matrix", args=[self.lesson.id])
        for url in (self.url, history, matrix):
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(self.url, {f"status_{e.id}": "absent"}).status_code, 403)
        self.assertFalse(AttendanceEntry.objects.exists())

    def test_logged_out_visitors_are_sent_to_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_instructors_can_still_open_every_register_page(self):
        history = reverse("anseo:attendance_history", args=[self.lesson.id, self.term.id])
        matrix = reverse("anseo:attendance_matrix", args=[self.lesson.id])
        for url in (self.url, history, matrix):
            self.assertEqual(self.client.get(url).status_code, 200)
