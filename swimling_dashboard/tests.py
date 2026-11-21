from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from users.models import Swimling


class MissingDetailsReminderTests(TestCase):
    """Families back after archiving have lost their children's DOB and medical info."""

    def setUp(self):
        self.parent = get_user_model().objects.create_user(
            email="parent@example.com", password="pw-123456!", first_name="Ann")
        self.parent.groups.add(Group.objects.get_or_create(name="Guardian")[0])
        self.client.force_login(self.parent)
        self.url = reverse("swimling_dashboard:guardian_dashboard")

    def test_asks_for_details_of_a_swimmer_with_no_date_of_birth(self):
        Swimling.objects.create(guardian=self.parent, first_name="Cara", dob=None)
        Swimling.objects.create(guardian=self.parent, first_name="Dara", dob=date(2016, 1, 1))
        response = self.client.get(self.url)
        self.assertContains(response, "Please check your swimmers' details")
        self.assertContains(response, "Update Cara")
        self.assertNotContains(response, "Update Dara")

    def test_no_reminder_when_details_are_complete(self):
        Swimling.objects.create(guardian=self.parent, first_name="Dara", dob=date(2016, 1, 1))
        self.assertNotContains(self.client.get(self.url), "Please check your swimmers' details")
