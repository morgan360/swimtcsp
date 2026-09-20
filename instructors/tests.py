from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from users.models import Swimling

User = get_user_model()


class SkillReportAccessTests(TestCase):
    """Progress reports name a child and carry their instructor notes.

    Both views were reachable anonymously, with the swimling id in the URL.
    """

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user(
            email="desk@tcsp.ie", password="pw", first_name="Desk"
        )
        cls.staff.is_staff = True
        cls.staff.save(update_fields=["is_staff"])

        cls.instructor = User.objects.create_user(
            email="coach@tcsp.ie", password="pw", first_name="Coach"
        )
        cls.instructor.groups.add(Group.objects.create(name="instructor"))

        cls.guardian = User.objects.create_user(
            email="parent@example.com", password="pw", first_name="Parent"
        )
        cls.guardian.groups.add(Group.objects.create(name="Guardian"))

        cls.swimling = Swimling.objects.create(
            first_name="Aoife",
            last_name="Byrne",
            dob=date.today() - timedelta(days=3000),
        )

    def _urls(self):
        return [
            reverse('instructors:category_skill_matrix'),
            reverse('instructors:generate_skill_report', args=[self.swimling.id]),
        ]

    def test_anonymous_visitors_are_sent_to_log_in(self):
        for url in self._urls():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/accounts/login/', response['Location'])

    def test_guardians_are_refused(self):
        self.client.force_login(self.guardian)
        for url in self._urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_instructors_are_allowed(self):
        self.client.force_login(self.instructor)
        for url in self._urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_staff_are_allowed(self):
        self.client.force_login(self.staff)
        for url in self._urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
