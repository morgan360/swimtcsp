from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class CalendarTabTests(TestCase):
    """The public found the Calendar tab confusing, so only staff see it."""

    url = reverse("timetable:timetable_grid")

    def test_public_do_not_see_the_calendar_tab(self):
        html = self.client.get(self.url).content.decode()
        self.assertNotIn("switchTab('calendar')", html)
        self.assertNotIn('id="calendar"', html)

    def test_staff_still_see_it(self):
        staff = get_user_model().objects.create_user(email="desk@tcsp.ie", password="pw")
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        self.client.force_login(staff)
        html = self.client.get(self.url).content.decode()
        self.assertIn("switchTab('calendar')", html)
