from datetime import timedelta
from decimal import Decimal

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


class ActivityReportTests(TestCase):
    """The finance panel's today / yesterday / this-week activity page."""

    @classmethod
    def setUpTestData(cls):
        from swims_orders.models import Order as SwimOrder
        from users.models import LoginEvent

        cls.manager = User.objects.create_user(email="manager@tcsp.ie", password="pw", first_name="M")
        cls.manager.is_staff = True
        cls.manager.save(update_fields=["is_staff"])
        cls.manager.groups.add(Group.objects.get_or_create(name="Manager")[0])
        cls.customer = User.objects.create_user(email="parent@example.com", password="pw", first_name="P")

        now = timezone.localtime()
        cls.yesterday_noon = now.replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(days=1)
        cls.yesterday_in_week = now.weekday() > 0

        SwimOrder.objects.create(user=cls.customer, paid=True, amount="6.50")
        SwimOrder.objects.create(user=cls.customer, paid=True, amount="5.00", payment_status="refunded")
        SwimOrder.objects.create(user=cls.customer, paid=False, amount="9.00")
        old = SwimOrder.objects.create(user=cls.customer, paid=True, amount="4.00")
        SwimOrder.objects.filter(pk=old.pk).update(created=cls.yesterday_noon)

        LoginEvent.objects.create(user=cls.customer)
        LoginEvent.objects.create(user=cls.customer)
        LoginEvent.objects.create(user=cls.manager)

        from users.models import ActiveDay
        ActiveDay.objects.create(user=cls.customer, date=now.date())
        ActiveDay.objects.create(user=cls.customer, date=cls.yesterday_noon.date())

    def rows(self):
        self.client.force_login(self.manager)  # itself logs a staff login
        response = self.client.get(reverse("finance:activity_report"))
        self.assertEqual(response.status_code, 200)
        return {(heading, row["label"]): row["values"] for heading, rows in response.context["sections"] for row in rows}

    def test_index_links_to_the_report(self):
        self.client.force_login(self.manager)
        self.assertContains(self.client.get(reverse("finance:index")), reverse("finance:activity_report"))

    def test_paid_swim_orders_by_period(self):
        rows = self.rows()
        week = 2 if self.yesterday_in_week else 1
        # Unpaid and refunded orders are left out.
        self.assertEqual(rows[("🏊 Public swims", "Paid orders")], [1, 1, week])
        today, yesterday, _ = rows[("🏊 Public swims", "Revenue")]
        self.assertEqual((today, yesterday), (Decimal("6.50"), Decimal("4.00")))
        self.assertEqual(rows[("💶 All orders", "Paid orders")], [1, 1, week])

    def test_logins_split_staff_and_customers(self):
        rows = self.rows()
        self.assertEqual(rows[("👪 Customers", "Logins")][0], 2)
        self.assertEqual(rows[("👪 Customers", "Customers who logged in")][0], 1)
        # The one created above, plus force_login in rows().
        self.assertEqual(rows[("🧑‍💼 Staff", "Logins")][0], 2)
        self.assertEqual(rows[("🧑‍💼 Staff", "Staff who logged in")][0], 1)

    def test_active_users(self):
        rows = self.rows()
        week = 1  # the same customer on two days is one person this week
        self.assertEqual(rows[("👪 Customers", "Active customers")], [1, 1, week])
        # rows() itself was a staff page view today.
        self.assertEqual(rows[("🧑‍💼 Staff", "Active staff")][0], 1)

    def test_panel_context_is_present(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("finance:activity_report"))
        self.assertIn("tcsp_panels", response.context)


class DashboardTests(TestCase):
    """The finance panel's live dashboard: dials, tiles and charts."""

    @classmethod
    def setUpTestData(cls):
        from anseo.models import AttendanceEntry, AttendanceRoll
        from swims.models import PriceVariant, PublicSwimCategory, PublicSwimProduct
        from swims_orders.models import Order as SwimOrder, OrderItem as SwimOrderItem

        cls.manager = User.objects.create_user(email="manager@tcsp.ie", password="pw", first_name="M")
        cls.manager.is_staff = True
        cls.manager.save(update_fields=["is_staff"])
        cls.manager.groups.add(Group.objects.get_or_create(name="Manager")[0])
        cls.staff = User.objects.create_user(email="staff@tcsp.ie", password="pw", first_name="S")
        cls.staff.is_staff = True
        cls.staff.save(update_fields=["is_staff"])
        customer = User.objects.create_user(email="parent@example.com", password="pw", first_name="P")

        now = timezone.localtime()
        today = now.date()
        cls.term = Term.objects.create(start_date=today - timedelta(days=10), end_date=today + timedelta(days=50))
        category = Category.objects.create(name="Beginners 1", program=Program.objects.create(name="P"))
        cls.lesson = Product.objects.create(category=category, day_of_week=0, num_places=5, active=True)
        kids = [Swimling.objects.create(guardian=customer, first_name=f"Kid{i}", last_name="T") for i in range(5)]
        enrolments = [LessonEnrollment.objects.create(lesson=cls.lesson, swimling=kid, term=cls.term)
                      for kid in kids]

        # Today's swims: 20 places in today's session, plus another day's that must not count.
        swims = PublicSwimCategory.objects.create(name="Lane Swim", slug="lane-swim")
        session = PublicSwimProduct.objects.create(category=swims, day_of_week=today.weekday(),
                                                   start_time=now.time().replace(hour=7, minute=0),
                                                   end_time=now.time().replace(hour=8, minute=0),
                                                   num_places=20, available=True)
        PublicSwimProduct.objects.create(category=swims, day_of_week=(today.weekday() + 1) % 7,
                                         start_time=session.start_time, end_time=session.end_time,
                                         num_places=50, available=True)
        variant = PriceVariant.objects.create(product=session, variant="Adult", price=8)

        def swim_order(booking, quantity, **kwargs):
            order = SwimOrder.objects.create(user=customer, product=session, booking=booking, amount="8.00", **kwargs)
            SwimOrderItem.objects.create(order=order, variant=variant, quantity=quantity)

        swim_order(today, 3, paid=True)
        swim_order(today, 2, paid=True, payment_status="refunded")
        swim_order(today, 4, paid=False)
        swim_order(today + timedelta(days=7), 6, paid=True)

        # Today's register: 2 present, 1 late, 1 absent and 1 not marked.
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        roll = AttendanceRoll.objects.create(product=cls.lesson, term=cls.term,
                                             window_start=day_start + timedelta(hours=8),
                                             window_end=day_start + timedelta(hours=16))
        statuses = [AttendanceEntry.PRESENT, AttendanceEntry.PRESENT, AttendanceEntry.LATE, AttendanceEntry.ABSENT,
                    AttendanceEntry.UNKNOWN]
        for enrolment, status in zip(enrolments, statuses):
            AttendanceEntry.objects.create(roll=roll, enrollment=enrolment, swimling_id=enrolment.swimling_id,
                                           status=status)

    def get(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("finance:dashboard"))
        self.assertEqual(response.status_code, 200)
        return response

    def dials(self):
        return {dial["title"]: dial for dial in self.get().context["dials"]}

    def test_index_links_to_the_dashboard(self):
        self.client.force_login(self.manager)
        self.assertContains(self.client.get(reverse("finance:index")), reverse("finance:dashboard"))

    def test_plain_staff_cannot_open_it(self):
        self.client.force_login(self.staff)
        self.assertIn(self.client.get(reverse("finance:dashboard")).status_code, (302, 403))

    def test_swims_dial_counts_todays_paid_swimmers(self):
        dial = self.dials()["Today’s public swims"]
        # Refunded, unpaid and next week's bookings are left out; so is the other day's session.
        self.assertEqual((dial["value"], dial["max"], dial["pct"]), (3, 20, 15))

    def test_attendance_ignores_unmarked_entries(self):
        dial = self.dials()["Today’s class attendance"]
        self.assertEqual((dial["value"], dial["max"], dial["pct"]), (3, 4, 75))
        self.assertEqual(dial["level"], "mid")

    def test_term_dial_matches_lesson_enrollments(self):
        self.client.force_login(self.manager)
        report = self.client.get(reverse("finance:lesson_enrollments")).context["term_summaries"]
        this = next(s for s in report if s["term"] == self.term)
        dial = self.dials()["This term’s lessons"]
        self.assertEqual((dial["value"], dial["max"]), (this["enrolled"], this["places"]))
        # 5 of 5: the needle is at full and the class counts as full.
        self.assertEqual((dial["pct"], dial["angle"], dial["level"]), (100, 90.0, "high"))
        self.assertEqual(self.get().context["term_fill"]["full"], 1)

    def test_no_next_term_hides_its_dial(self):
        self.assertNotIn("Next term booked", self.dials())

    def test_renders_with_no_terms_at_all(self):
        from anseo.models import AttendanceRoll
        AttendanceRoll.objects.all().delete()  # rolls protect their term
        Term.objects.all().delete()
        response = self.get()
        self.assertNotIn("This term’s lessons", [d["title"] for d in response.context["dials"]])
        self.assertIsNone(response.context["term_fill"])

    def test_charts_cover_fourteen_days(self):
        data = self.get().context["chart_data"]
        self.assertEqual(len(data["days"]), 14)
        self.assertEqual(len(data["customer_logins"]), 14)
        self.assertEqual(set(data["revenue"]), {"Lesson", "Swim", "School"})
        # Today's paid, non-refunded swim orders: the 3-swimmer order and next week's booking (both placed today).
        self.assertEqual(data["revenue"]["Swim"][-1], 16.0)
