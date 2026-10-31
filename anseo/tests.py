import re
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from anseo.models import AttendanceEntry, AttendanceRoll
from lessons.models import Category, Product, Program
from lessons_bookings.models import LessonAssignment, LessonEnrollment, Term
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


class PhoneRegisterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.instructor = User.objects.create_user(email="instructor@tcsp.ie", password="pw", first_name="I")
        cls.instructor.groups.add(Group.objects.create(name="instructor"))
        cls.parent = User.objects.create_user(email="parent@example.com", password="pw", first_name="P")
        cls.today = timezone.localdate()
        cls.term = Term.objects.create(start_date=cls.today - timedelta(days=30),
                                       end_date=cls.today + timedelta(days=60))
        category = Category.objects.create(name="Beginners 2", program=Program.objects.create(name="P"))

        def lesson(day_of_week, start):
            return Product.objects.create(category=category, day_of_week=day_of_week, num_places=6, active=True,
                                          start_time=start, end_time=time(23, 59))

        cls.lesson_today = lesson(cls.today.weekday(), time(0, 0))
        cls.yesterday = cls.today - timedelta(days=1)
        cls.lesson_yesterday = lesson(cls.yesterday.weekday(), time(15, 30))
        cls.not_mine = lesson(cls.today.weekday(), time(0, 1))
        cls.enrolments = {}
        for product in (cls.lesson_today, cls.lesson_yesterday, cls.not_mine):
            cls.enrolments[product.id] = [
                LessonEnrollment.objects.create(
                    lesson=product, term=cls.term,
                    swimling=Swimling.objects.create(guardian=cls.parent, first_name=f"Kid{i}", last_name="T"),
                )
                for i in range(2)
            ]
        assignment = LessonAssignment.objects.create(instructor=cls.instructor, term=cls.term)
        assignment.lessons.add(cls.lesson_today, cls.lesson_yesterday)

    def setUp(self):
        self.client.force_login(self.instructor)

    def roll_url(self, lesson, day):
        return reverse("anseo:phone_roll", args=[lesson.id, day.isoformat()])

    def test_parents_cannot_open_the_registers(self):
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(reverse("anseo:registers")).status_code, 403)
        self.assertEqual(self.client.get(self.roll_url(self.lesson_today, self.today)).status_code, 403)

    def test_list_shows_my_classes_and_yesterdays_as_missed(self):
        response = self.client.get(reverse("anseo:registers"))
        self.assertEqual([r["lesson_id"] for r in response.context["today_rows"]], [self.lesson_today.id])
        self.assertEqual([r["lesson_id"] for r in response.context["missed_rows"]], [self.lesson_yesterday.id])

    def test_all_shows_classes_being_covered(self):
        response = self.client.get(reverse("anseo:registers"), {"all": "1"})
        self.assertIn(self.not_mine.id, [r["lesson_id"] for r in response.context["today_rows"]])

    def test_everyone_starts_as_here(self):
        response = self.client.get(self.roll_url(self.lesson_today, self.today))
        self.assertEqual({r["status"] for r in response.context["rows"]}, {"present"})
        self.assertFalse(AttendanceRoll.objects.exists())  # opening it leaves no empty roll

    def test_late_register_is_dated_by_the_class_not_when_it_was_marked(self):
        first, second = self.enrolments[self.lesson_yesterday.id]
        response = self.client.post(self.roll_url(self.lesson_yesterday, self.yesterday), {
            f"status_{first.id}": "present", f"status_{second.id}": "absent", f"note_{second.id}": "Ill",
        })
        self.assertRedirects(response, reverse("anseo:registers"))
        roll = AttendanceRoll.objects.get()
        self.assertEqual(timezone.localtime(roll.window_start).date(), self.yesterday)
        self.assertEqual(AttendanceEntry.objects.get(enrollment=second).note, "Ill")
        response = self.client.get(reverse("anseo:registers"))
        self.assertEqual(response.context["missed_rows"], [])

    def test_saving_again_updates_the_tablets_roll_instead_of_splitting_it(self):
        e = self.enrolments[self.lesson_today.id][0]
        self.client.post(reverse("anseo:take_roll", args=[self.lesson_today.id, self.term.id]),
                         {f"status_{e.id}": "late"})
        self.client.post(self.roll_url(self.lesson_today, self.today), {f"status_{e.id}": "absent"})
        self.assertEqual(AttendanceRoll.objects.count(), 1)
        self.assertEqual(AttendanceEntry.objects.get(enrollment=e).status, "absent")

    def test_tablet_catch_up_days_later_counts_for_the_class(self):
        e = self.enrolments[self.lesson_yesterday.id][0]
        window = timezone.make_aware(datetime.combine(self.today, time(0)))
        roll = AttendanceRoll.objects.create(product=self.lesson_yesterday, term=self.term,
                                             window_start=window, window_end=window + timedelta(hours=8))
        AttendanceEntry.objects.create(roll=roll, enrollment=e, swimling_id=e.swimling_id, status="present")
        self.assertEqual(self.client.get(reverse("anseo:registers")).context["missed_rows"], [])

    def test_wrong_weekday_future_and_bad_dates_are_refused(self):
        wrong = self.today - timedelta(days=2)
        future = self.today + timedelta(days=7)
        for url in (self.roll_url(self.lesson_today, wrong), self.roll_url(self.lesson_today, future),
                    f"/anseo/registers/{self.lesson_today.id}/nonsense/"):
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_unknown_status_clears_instead_of_saving(self):
        e = self.enrolments[self.lesson_today.id][0]
        self.client.post(self.roll_url(self.lesson_today, self.today), {f"status_{e.id}": "banana"})
        self.assertFalse(AttendanceEntry.objects.exists())
