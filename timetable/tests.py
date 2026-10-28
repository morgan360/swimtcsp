from datetime import date, timedelta

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


class ClosureFixtures:
    """A public swim and a lesson every day of the week, 20 swim places each."""

    @classmethod
    def setUpTestData(cls):
        from datetime import time

        from lessons.models import Category, Product, Program
        from swims.models import PriceVariant, PublicSwimCategory, PublicSwimProduct

        cls.today = date.today()
        swims = PublicSwimCategory.objects.create(name="Lane Swim", slug="lane-swim")
        cls.swims = [
            PublicSwimProduct.objects.create(category=swims, day_of_week=day, start_time=time(0, 0),
                                             end_time=time(23, 59), num_places=20, available=True)
            for day in range(7)
        ]
        cls.variant = PriceVariant.objects.create(product=cls.swims[cls.today.weekday()], variant="Adult", price=8)
        category = Category.objects.create(name="Beginners 1", program=Program.objects.create(name="P"))
        for day in range(7):
            Product.objects.create(category=category, day_of_week=day, num_places=5, active=True,
                                   start_time=time(17, 0), end_time=time(17, 30))
        cls.customer = get_user_model().objects.create_user(email="parent@example.com", password="pw")

    def close(self, day, affects="all", title="Bank holiday", end=None):
        from timetable.models import CalendarEvent

        return CalendarEvent.objects.create(title=title, category="closure", affects=affects,
                                            start_date=day, end_date=end)

    def book(self, day, quantity, **kwargs):
        from swims_orders.models import Order, OrderItem

        product = self.swims[day.weekday()]
        order = Order.objects.create(user=self.customer, product=product, booking=day, amount="8.00", **kwargs)
        OrderItem.objects.create(order=order, variant=self.variant, quantity=quantity)


class ClosuresTests(ClosureFixtures, TestCase):
    """Closures staff record in Operations decide what customers are told is on."""

    def test_a_closure_covers_its_whole_range_and_a_one_day_closure_its_day(self):
        from timetable.closures import closures_between

        week = self.close(self.today, end=self.today + timedelta(days=4), title="Midterm")
        one_day = self.close(self.today + timedelta(days=10))
        self.close(self.today + timedelta(days=30))
        self.assertEqual(closures_between(self.today + timedelta(days=2), self.today + timedelta(days=10)),
                         [week, one_day])

    def test_scopes_stop_only_what_they_say(self):
        from timetable.closures import closure_for

        lessons_off = self.close(self.today, affects="lessons", title="Midterm")
        self.assertIsNone(closure_for("swim", self.today, [lessons_off]))
        self.assertEqual(closure_for("lesson", self.today, [lessons_off]), lessons_off)
        whole = self.close(self.today, affects="all")
        self.assertEqual(closure_for("swim", self.today, [whole]), whole)

    def test_other_categories_are_not_closures(self):
        from timetable.closures import closures_between
        from timetable.models import CalendarEvent

        CalendarEvent.objects.create(title="Term starts", category="term", start_date=self.today)
        self.assertEqual(closures_between(self.today, self.today), [])


class TimetableApiTests(ClosureFixtures, TestCase):

    def swim_week(self):
        response = self.client.get(reverse("timetable:public_timetable"), {"start": self.today.isoformat()})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_closed_day_is_flagged_on_the_day_and_its_sessions(self):
        self.close(self.today + timedelta(days=1), title="Bank holiday")
        data = self.swim_week()
        self.assertEqual(data["days"][1]["closures"], [{"title": "Bank holiday", "affects": "all"}])
        self.assertEqual(data["days"][0]["closures"], [])
        closed = {e["date"]: e["closed"] for e in data["events"]}
        self.assertEqual(closed[(self.today + timedelta(days=1)).isoformat()], "Bank holiday")
        self.assertIsNone(closed[self.today.isoformat()])

    def test_lessons_only_closure_leaves_swims_open(self):
        self.close(self.today, affects="lessons", title="Midterm")
        swim_today = next(e for e in self.swim_week()["events"] if e["date"] == self.today.isoformat())
        self.assertIsNone(swim_today["closed"])
        lessons = self.client.get(reverse("timetable:weekly_timetable"), {"start": self.today.isoformat()}).json()
        lesson_today = next(e for e in lessons["events"] if e["date"] == self.today.isoformat())
        self.assertEqual(lesson_today["closed"], "Midterm")

    def test_places_left_counts_paid_unrefunded_swimmers_as_the_dashboard_does(self):
        self.book(self.today, 3, paid=True)
        self.book(self.today, 2, paid=True, payment_status="refunded")
        self.book(self.today, 4, paid=False)
        swim_today = next(e for e in self.swim_week()["events"] if e["date"] == self.today.isoformat())
        self.assertEqual(swim_today["places_left"], 17)
        self.assertTrue(swim_today["book_url"].startswith("/swims/"))

    def test_places_never_go_below_zero(self):
        self.book(self.today, 25, paid=True)
        swim_today = next(e for e in self.swim_week()["events"] if e["date"] == self.today.isoformat())
        self.assertEqual(swim_today["places_left"], 0)


class SwimBookingOnClosedDayTests(ClosureFixtures, TestCase):
    """The booking page must not take money for a day the timetable shows closed."""

    def setUp(self):
        self.client.force_login(self.customer)
        product = self.swims[self.today.weekday()]
        self.url = reverse("swims:product_detail", args=[product.id, product.slug])

    def test_closed_day_shows_why_and_refuses_the_booking(self):
        from swims_orders.models import Order

        self.close(self.today, title="Bank holiday")
        page = self.client.get(self.url)
        self.assertContains(page, "No public swimming on")
        self.assertContains(page, "Bank holiday")
        response = self.client.post(self.url, {f"quantity_{self.variant.id}": 1})
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertFalse(Order.objects.exists())

    def test_lessons_only_closure_does_not_stop_swim_booking(self):
        self.close(self.today, affects="lessons", title="Midterm")
        self.assertNotContains(self.client.get(self.url), "No public swimming on")


class HomepageTodayTests(ClosureFixtures, TestCase):
    """The homepage answers "is the pool open today?" itself."""

    def test_open_day_lists_todays_swims_with_places(self):
        self.book(self.today, 5, paid=True)
        page = self.client.get(reverse("home"))
        self.assertContains(page, "Open today")
        self.assertContains(page, "15 places left")
        self.assertContains(page, "Lessons on as usual")

    def test_closed_day_says_so_and_why(self):
        self.close(self.today, title="Christmas")
        page = self.client.get(reverse("home"))
        self.assertContains(page, "Closed today: Christmas")
        self.assertNotContains(page, "places left")

    def test_lessons_off_but_swims_on(self):
        self.close(self.today, affects="lessons", title="Midterm")
        page = self.client.get(reverse("home"))
        self.assertContains(page, "Open today")
        self.assertContains(page, "No lessons today: Midterm")
        self.assertContains(page, "places left")


class TimetablePageTests(TestCase):

    def test_page_opens_on_the_day_view(self):
        html = self.client.get(reverse("timetable:timetable_grid")).content.decode()
        self.assertIn("dayStatus(selectedDay)", html)
        self.assertIn("See the whole week", html)


class StaticCacheBustingTests(TestCase):
    """Browsers kept an old timetable.js after the day view shipped, leaving it
    blank; the asset URLs change with every deploy so they fetch the new one."""

    def test_script_and_stylesheet_carry_the_version(self):
        from django.conf import settings

        html = self.client.get(reverse("timetable:timetable_grid")).content.decode()
        self.assertIn(f"js/timetable.js?v={settings.VERSION}", html)
        self.assertIn(f"css/styles.css?v={settings.VERSION}", html)
