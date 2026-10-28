from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class CalendarTabTests(TestCase):
    """The Calendar tab is a plain 12-month view for everyone (Oct 2026); the
    old FullCalendar one confused parents, so it had been staff-only."""

    url = reverse("timetable:timetable_grid")

    def test_everyone_sees_the_calendar_tab_without_fullcalendar(self):
        html = self.client.get(self.url).content.decode()
        self.assertIn("switchTab('calendar')", html)
        self.assertIn("Coming up", html)
        self.assertNotIn("{#", html)
        self.assertNotIn("fullcalendar", html.lower())


class YearCalendarTests(TestCase):
    """timetable.year: lesson starts, rebooking, booking and closures only."""

    @classmethod
    def setUpTestData(cls):
        from datetime import time

        from lessons.models import Category, Product, Program

        category = Category.objects.create(name="Beginners 1", program=Program.objects.create(name="P"))
        # Lessons on Mondays and Wednesdays only.
        for day in (0, 2):
            Product.objects.create(category=category, day_of_week=day, num_places=5, active=True,
                                   start_time=time(17, 0), end_time=time(17, 30))

    def setUp(self):
        from lessons_bookings.models import Term

        self.today = date(2026, 10, 28)
        # Starts Thursday 1 Jan 2027, like terms that run 1st to last of the month.
        self.term = Term.objects.create(start_date=date(2027, 1, 1), end_date=date(2027, 3, 31),
                                        rebooking_date=date(2026, 12, 1), booking_date=date(2026, 12, 8))

    def build(self):
        from timetable.year import year_calendar

        return year_calendar(self.today)

    def marks_on(self, year, day):
        for month in year["months"]:
            for week in month["weeks"]:
                for d in week:
                    if d["date"] == day and d["in_month"]:
                        return [m["kind"] for m in d["marks"]]
        return None

    def test_twelve_months_from_this_month(self):
        months = [m["first"] for m in self.build()["months"]]
        self.assertEqual((len(months), months[0], months[-1]), (12, date(2026, 10, 1), date(2027, 9, 1)))

    def test_rebooking_and_booking_dates_are_marked(self):
        year = self.build()
        self.assertEqual(self.marks_on(year, date(2026, 12, 1)), ["rebooking"])
        self.assertEqual(self.marks_on(year, date(2026, 12, 8)), ["booking"])

    def test_lessons_start_on_the_first_class_day_not_the_1st(self):
        # 1 Jan is a Thursday; the first lesson day is Monday 4 Jan.
        year = self.build()
        self.assertEqual(self.marks_on(year, date(2027, 1, 1)), [])
        self.assertEqual(self.marks_on(year, date(2027, 1, 4)), ["start"])

    def test_lessons_start_skips_a_lessons_closure(self):
        from timetable.models import CalendarEvent

        CalendarEvent.objects.create(title="Christmas", category="closure", affects="lessons",
                                     start_date=date(2026, 12, 20), end_date=date(2027, 1, 5))
        year = self.build()
        self.assertEqual(self.marks_on(year, date(2027, 1, 6)), ["start"])
        self.assertEqual(self.marks_on(year, date(2027, 1, 4)), ["closed"])

    def test_a_closure_marks_each_day_and_is_one_key_date(self):
        from timetable.models import CalendarEvent

        CalendarEvent.objects.create(title="Midterm", category="closure", affects="all",
                                     start_date=date(2027, 2, 15), end_date=date(2027, 2, 19))
        year = self.build()
        for day in range(15, 20):
            self.assertEqual(self.marks_on(year, date(2027, 2, day)), ["closed"])
        closures = [k for k in year["key_dates"] if k["kind"] == "closed"]
        self.assertEqual([(k["first"], k["last"], k["label"]) for k in closures],
                         [(date(2027, 2, 15), date(2027, 2, 19), "Pool closed: Midterm")])

    def test_coming_up_leaves_out_past_dates(self):
        from timetable.year import year_calendar

        upcoming = year_calendar(date(2026, 12, 5))["upcoming"]
        self.assertEqual([k["label"] for k in upcoming],
                         ["Booking opens to everyone", "Lessons start"])

    def test_school_terms_and_other_events_are_left_out(self):
        from timetable.models import CalendarEvent

        CalendarEvent.objects.create(title="Open day", category="special", start_date=date(2026, 11, 5))
        labels = [k["label"] for k in self.build()["key_dates"]]
        self.assertNotIn("Open day", " ".join(labels))
        self.assertEqual(len(labels), 3)  # rebooking, booking, lessons start


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
        self.assertTrue(swim_today["book_url"].startswith("/timetable/book/"))

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


BROWSER = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604.1"


class TimetableVisitTests(ClosureFixtures, TestCase):
    """How often the timetable is used: a count per page per day, nothing more."""

    def count(self, page):
        from timetable.models import PageVisit

        row = PageVisit.objects.filter(page=page).first()
        return row.count if row else 0

    def test_timetable_and_homepage_views_are_counted(self):
        self.client.get(reverse("timetable:timetable_grid"), HTTP_USER_AGENT=BROWSER)
        self.client.get(reverse("timetable:timetable_grid"), HTTP_USER_AGENT=BROWSER)
        self.client.get(reverse("home"), HTTP_USER_AGENT=BROWSER)
        self.assertEqual((self.count("timetable"), self.count("home")), (2, 1))

    def test_bots_and_staff_are_not_counted(self):
        self.client.get(reverse("timetable:timetable_grid"), HTTP_USER_AGENT="Googlebot/2.1")
        self.client.get(reverse("timetable:timetable_grid"))  # no user agent
        staff = get_user_model().objects.create_user(email="desk@tcsp.ie", password="pw")
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        self.client.force_login(staff)
        self.client.get(reverse("timetable:timetable_grid"), HTTP_USER_AGENT=BROWSER)
        self.assertEqual(self.count("timetable"), 0)

    def test_staff_impersonating_a_customer_are_not_counted(self):
        self.client.force_login(self.customer)
        session = self.client.session
        session["hijack_history"] = ["1"]
        session.save()
        self.client.get(reverse("timetable:timetable_grid"), HTTP_USER_AGENT=BROWSER)
        self.assertEqual(self.count("timetable"), 0)

    def test_tab_pings_count_known_tabs_only(self):
        url = reverse("timetable:tab_seen")
        self.assertEqual(self.client.post(url, {"tab": "calendar"}, HTTP_USER_AGENT=BROWSER).status_code, 204)
        self.client.post(url, {"tab": "anything"}, HTTP_USER_AGENT=BROWSER)
        from timetable.models import PageVisit

        self.assertEqual(list(PageVisit.objects.values_list("page", "count")), [("tab:calendar", 1)])

    def test_book_click_is_counted_then_goes_to_the_booking_page(self):
        product = self.swims[self.today.weekday()]
        response = self.client.get(reverse("timetable:book_swim", args=[product.id]) + "?via=home",
                                   HTTP_USER_AGENT=BROWSER)
        self.assertRedirects(response, reverse("swims:product_detail", args=[product.id, product.slug]),
                             fetch_redirect_response=False)
        self.assertEqual(self.count("book:home"), 1)

    def test_homepage_card_book_links_go_through_the_counter(self):
        page = self.client.get(reverse("home"), HTTP_USER_AGENT=BROWSER).content.decode()
        self.assertIn("/timetable/book/", page)
        self.assertIn("?via=home", page)
