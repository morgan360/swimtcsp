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

    def test_confirmed_email_dial_counts_guardians_as_the_reminder_does(self):
        from allauth.account.models import EmailAddress
        from allauth.socialaccount.models import SocialAccount

        parent = User.objects.get(email="parent@example.com")
        dial = self.dials()["Guardians with confirmed email"]
        self.assertEqual((dial["value"], dial["max"]), (0, 1))

        # Google's word counts, for the same address only.
        google = SocialAccount.objects.create(user=parent, provider="google", uid="g1",
                                              extra_data={"email": "other@gmail.com", "email_verified": True})
        self.assertEqual(self.dials()["Guardians with confirmed email"]["value"], 0)
        google.extra_data = {"email": "Parent@example.com", "email_verified": True}
        google.save()
        self.assertEqual(self.dials()["Guardians with confirmed email"]["value"], 1)

        google.delete()
        EmailAddress.objects.create(user=parent, email="PARENT@example.com", verified=True, primary=True)
        self.assertEqual(self.dials()["Guardians with confirmed email"]["value"], 1)

    def test_timetable_use_tiles(self):
        from timetable.models import PageVisit

        today = timezone.localdate()
        PageVisit.objects.create(date=today, page=PageVisit.TIMETABLE, count=7)
        PageVisit.objects.create(date=today, page=PageVisit.TAB_CALENDAR, count=2)
        PageVisit.objects.create(date=today, page=PageVisit.BOOK_TIMETABLE, count=3)
        PageVisit.objects.create(date=today, page=PageVisit.BOOK_HOME, count=1)
        tiles = {t["label"]: t for t in self.get().context["tiles"]}
        self.assertEqual(tiles["Timetable views"]["today"], 7)
        self.assertIn("2 calendar", tiles["Timetable views"]["hint"])
        self.assertEqual(tiles["Book clicks"]["today"], 4)
        self.assertIn("3 from the timetable, 1 from the homepage", tiles["Book clicks"]["hint"])

    def test_every_dial_and_tile_is_in_a_section(self):
        context = self.get().context
        sections = context["sections"]
        self.assertEqual(list(sections), ["enrolments", "security", "operations", "admin", "finance"])
        placed_dials = [d["title"] for s in sections.values() for d in s["dials"]]
        placed_tiles = [t["label"] for s in sections.values() for t in s["tiles"]]
        self.assertCountEqual(placed_dials, [d["title"] for d in context["dials"]])
        self.assertCountEqual(placed_tiles, [t["label"] for t in context["tiles"]])

    def test_coupon_values(self):
        from django.contrib.contenttypes.models import ContentType
        from coupons.models import Coupon, CouponRedemption

        current = timezone.now()
        day = timedelta(days=1)

        def coupon(code, value, balance, **kwargs):
            fields = {"discount_type": "fixed", "valid_from": current - day, "valid_to": current + day, **kwargs}
            return Coupon.objects.create(code=code, discount_value=value, balance_remaining=balance, **fields)

        usable = coupon("USABLE", 50, 30)
        coupon("SPENT", 20, Decimal("0.01"), valid_to=current - day)  # expired, a cent left
        coupon("OFF", 40, 40, active=False)  # switched off: in neither figure
        coupon("MULTI", 10, 10, multi_use=True)
        coupon("PERCENT", 25, 25, discount_type="percent")

        target = {"content_type": ContentType.objects.get_for_model(Coupon), "object_id": usable.id}
        CouponRedemption.objects.create(coupon=usable, redeemed_amount=20, confirmed=True, **target)
        CouponRedemption.objects.create(coupon=usable, redeemed_amount=99, confirmed=False, **target)
        old = CouponRedemption.objects.create(coupon=usable, redeemed_amount=5, confirmed=True, **target)
        CouponRedemption.objects.filter(id=old.id).update(redeemed_at=current - timedelta(days=30))

        response = self.get()
        totals = response.context["coupons"]
        self.assertEqual((totals["unused"]["value"], totals["unused"]["count"]), (Decimal("30"), 1))
        self.assertEqual((totals["expired"]["value"], totals["expired"]["count"]), (Decimal("0.01"), 1))
        self.assertEqual(totals["used_week"]["value"], Decimal("20"))
        self.assertEqual((totals["used_all"]["value"], totals["used_all"]["count"]), (Decimal("25"), 2))
        self.assertEqual(totals["multi_use"], 1)
        self.assertNotContains(response, "USABLE")

    def test_security_incidents_are_shown(self):
        from security.models import SecurityIncident

        SecurityIncident.objects.create(kind="probe_blocked", ip="203.0.113.9", path="/wp-login.php")
        response = self.get()
        self.assertContains(response, "203.0.113.9")
        tiles = {t["label"]: t for t in response.context["tiles"]}
        self.assertEqual(tiles["Attackers blocked"]["today"], 1)

    def section_links(self):
        sections = self.get().context["sections"]
        return {key: [l["url"] for l in s.get("links", [])] for key, s in sections.items()}

    def test_sections_link_to_their_full_figures(self):
        from django.contrib.auth.models import Permission

        self.manager.user_permissions.add(
            Permission.objects.get(codename="view_coupon"), Permission.objects.get(codename="view_securityincident"))
        urls = self.section_links()
        self.assertEqual(urls["finance"], [reverse("finance:revenue_report"), reverse("finance:reconciliation"),
                                           reverse("finance:coupons_coupon_changelist"),
                                           reverse("finance:activity_report")])
        self.assertEqual(urls["enrolments"], [reverse("finance:lesson_enrollments")])
        self.assertEqual(urls["security"], [reverse("settings:security_securityincident_changelist")])
        for url in urls["finance"] + urls["enrolments"] + urls["security"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_links_someone_cannot_open_are_left_out(self):
        urls = self.section_links()
        self.assertNotIn(reverse("finance:coupons_coupon_changelist"), urls["finance"])
        self.assertEqual(urls["security"], [])
        self.assertEqual(len(urls["finance"]), 3)

    def test_unrecorded_registers_lists_classes_with_nothing_marked(self):
        from datetime import datetime, time

        from anseo.models import AttendanceEntry, AttendanceRoll
        from timetable.models import CalendarEvent
        from finances.views import _unrecorded_registers

        monday = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        category = Category.objects.create(name="Reg", program=Program.objects.create(name="R"))
        parent = User.objects.create_user(email="reg@example.com", password="pw", first_name="R")
        kid = Swimling.objects.create(guardian=parent, first_name="K", last_name="T")

        def lesson(name, day, hour=9):
            product = Product.objects.create(category=category, name=name, day_of_week=day, num_places=5,
                                             active=True, start_time=time(hour), end_time=time(hour, 30))
            enrolment = LessonEnrollment.objects.create(lesson=product, swimling=kid, term=self.term)
            return product, enrolment

        lesson("Missed", 2)
        marked, enrolment = lesson("Marked", 2)
        lesson("Closed", 3)
        lesson("Not started", 2, hour=18)
        window = timezone.make_aware(datetime.combine(monday + timedelta(days=2), time(8)))
        roll = AttendanceRoll.objects.create(product=marked, term=self.term, window_start=window,
                                             window_end=window + timedelta(hours=8))
        AttendanceEntry.objects.create(roll=roll, enrollment=enrolment, swimling_id=kid.id,
                                       status=AttendanceEntry.PRESENT)
        CalendarEvent.objects.create(title="Shut", category="closure", affects="lessons",
                                     start_date=monday + timedelta(days=3))

        # As if it were Thursday at noon.
        result = _unrecorded_registers(monday + timedelta(days=3), time(12))
        names = [row["name"] for row in result["rows"]]
        self.assertIn("Missed", names)
        self.assertIn("Not started", names)  # Wednesday's has happened by Thursday
        self.assertNotIn("Marked", names)
        self.assertNotIn("Closed", names)

        # Wednesday at noon: the 18:00 class hasn't started.
        names = [r["name"] for r in _unrecorded_registers(monday + timedelta(days=2), time(12))["rows"]]
        self.assertIn("Missed", names)
        self.assertNotIn("Not started", names)

    def test_unrecorded_registers_page_opens_from_operations(self):
        url = reverse("finance:unrecorded_registers")
        self.assertIn(url, self.section_links()["operations"])
        self.assertContains(self.client.get(url), "Classes with unrecorded registers")
        self.assertContains(self.client.get(url + "?week=last"), "Last week")

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

    def test_attendance_counts_unmarked_entries(self):
        dial = self.dials()["Swimmers’ attendance today"]
        self.assertEqual((dial["value"], dial["max"], dial["pct"]), (3, 5, 60))
        self.assertEqual(dial["caption"], "present or late · 1 not marked")
        self.assertEqual(dial["level"], "mid")

    def test_term_dial_has_no_target_without_a_previous_term(self):
        dial = self.dials()["This term’s lessons"]
        self.assertIsNone(dial["target_angle"])
        self.assertNotContains(self.get(), 'class="target"')

    def test_term_dial_marks_last_terms_fill(self):
        today = timezone.localdate()
        last = Term.objects.create(start_date=today - timedelta(days=80), end_date=today - timedelta(days=20))
        for kid in Swimling.objects.all()[:2]:
            LessonEnrollment.objects.create(lesson=self.lesson, swimling=kid, term=last)
        dial = self.dials()["This term’s lessons"]
        # 2 of 5 places last term: 40%, so the marker sits at -90 + 1.8 * 40 degrees.
        self.assertEqual((dial["target"], dial["target_angle"]), (40, -18.0))
        self.assertContains(self.get(), "Last term: 40%")

    def test_term_dial_matches_lesson_enrollments(self):
        self.client.force_login(self.manager)
        report = self.client.get(reverse("finance:lesson_enrollments")).context["term_summaries"]
        this = next(s for s in report if s["term"] == self.term)
        dial = self.dials()["This term’s lessons"]
        self.assertEqual((dial["value"], dial["max"]), (this["enrolled"], this["places"]))
        # 5 of 5: the needle is at full and the class counts as full.
        self.assertEqual((dial["pct"], dial["angle"], dial["level"]), (100, 90.0, "high"))
        self.assertEqual(self.get().context["term_fill"]["full"], 1)

    def test_registers_taken_this_week(self):
        dial = self.dials()["Classes’ attendance recorded this week"]
        # The one Monday lesson is always due by today, and today's register for it is marked.
        self.assertEqual((dial["value"], dial["max"]), (1, 1))

    def test_registers_dial_ignores_registers_nobody_marked(self):
        from anseo.models import AttendanceEntry
        AttendanceEntry.objects.update(status=AttendanceEntry.UNKNOWN)
        dial = self.dials()["Classes’ attendance recorded this week"]
        self.assertEqual((dial["value"], dial["max"]), (0, 1))

    def test_old_finances_dashboard_url_is_not_the_live_dashboard(self):
        # The live dashboard once shared the name ``dashboard`` with the older view
        # behind /finances/dashboard/, replacing it there without the Finance panel's
        # Manager/Full-Timer check.
        from django.urls import resolve
        from finances import views
        self.assertIs(resolve("/finances/dashboard/").func, views.dashboard)
        self.assertIsNot(views.dashboard, views.live_dashboard)

    def test_operations_home_shows_the_strip_to_any_staff(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("operations:index"))
        self.assertEqual(response.status_code, 200)
        titles = [d["title"] for d in response.context["dial_strip"]]
        self.assertEqual(titles, ["Today’s public swims", "Classes’ attendance recorded this week",
                                  "Swimmers’ attendance today", "This term’s lessons"])
        # Plain staff cannot open Finance, so no link to it and no money on the page.
        self.assertIsNone(response.context["live_dashboard_url"])
        self.assertNotContains(response, "Full dashboard")
        self.assertNotContains(response, "€")

    def test_operations_strip_links_finance_users_to_the_dashboard(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("operations:index"))
        self.assertContains(response, reverse("finance:dashboard"))

    def test_operations_section_pages_go_without_the_strip(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse("operations:section", args=["lessons"]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("dial_strip", response.context)

    def test_two_factor_dials(self):
        from allauth.mfa.models import Authenticator
        Authenticator.objects.create(user=self.manager, type=Authenticator.Type.TOTP, data={})
        Authenticator.objects.create(user=self.manager, type=Authenticator.Type.RECOVERY_CODES, data={})
        # Recovery codes on their own are not an authenticator app.
        Authenticator.objects.create(user=self.staff, type=Authenticator.Type.RECOVERY_CODES, data={})
        guardian = Swimling.objects.first().guardian
        Authenticator.objects.create(user=guardian, type=Authenticator.Type.TOTP, data={})
        # A customer with no swimmer is not counted as a guardian.
        User.objects.create_user(email="swimmer@example.com", password="pw", first_name="S")

        dials = self.dials()
        self.assertEqual((dials["Staff with 2FA"]["value"], dials["Staff with 2FA"]["max"]), (1, 2))
        self.assertEqual((dials["Guardians with 2FA"]["value"], dials["Guardians with 2FA"]["max"]), (1, 1))

    def test_two_factor_dials_stay_off_the_operations_strip(self):
        self.client.force_login(self.staff)
        titles = [d["title"] for d in self.client.get(reverse("operations:index")).context["dial_strip"]]
        self.assertNotIn("Staff with 2FA", titles)

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


class DashboardChatTests(TestCase):
    """The AI chat figures on the live dashboard."""

    @classmethod
    def setUpTestData(cls):
        from chatbot.models import ChatbotQuery

        def staff_member(email, group):
            user = User.objects.create_user(email=email, password="pw", first_name="S")
            user.is_staff = True
            user.save(update_fields=["is_staff"])
            user.groups.add(Group.objects.get_or_create(name=group)[0])
            return user

        cls.manager = staff_member("manager@tcsp.ie", "Manager")
        cls.full_timer = staff_member("full@tcsp.ie", "Full-Timer")
        customer = User.objects.create_user(email="parent@example.com", password="pw", first_name="P")

        def chat(response_type, message="When is the next lane swim?", **kwargs):
            return ChatbotQuery.objects.create(source="public_swim", message=message,
                                               response_type=response_type, **kwargs)

        chat("FAQ")
        chat("FAQ_HEDGED")
        chat("GPT", user=customer)
        chat("GPT")
        chat("BLOCKED", message="something abusive")
        old = chat("GPT")
        ChatbotQuery.objects.filter(pk=old.pk).update(timestamp=timezone.now() - timedelta(days=30))

    def get(self, user=None):
        self.client.force_login(user or self.manager)
        response = self.client.get(reverse("finance:dashboard"))
        self.assertEqual(response.status_code, 200)
        return response

    def test_tile_counts_questions_by_period(self):
        tile = next(t for t in self.get().context["tiles"] if t["label"] == "AI chat questions")
        self.assertEqual(tile["today"], 5)
        self.assertEqual(tile["hint"], "This week: 2 by the AI model, 2 from the FAQ")

    def test_chart_splits_by_answer_type(self):
        chats = self.get().context["chart_data"]["chats"]
        self.assertEqual({label: values[-1] for label, values in chats.items()},
                         {"FAQ answer": 1, "FAQ, unsure": 1, "AI model": 2, "Blocked": 1})

    def test_recent_questions_hide_blocked_text(self):
        response = self.get()
        recent = response.context["recent_chats"]
        self.assertEqual(len(recent), 6)
        self.assertEqual([c["message"] for c in recent if c["type"] == "BLOCKED"], [""])
        self.assertNotContains(response, "something abusive")

    def test_chat_log_link_only_for_settings_users(self):
        self.assertIsNotNone(self.get().context["chat_log_url"])
        self.assertIsNone(self.get(self.full_timer).context["chat_log_url"])

    def test_recent_questions_show_formatted_answer(self):
        from chatbot.models import ChatbotQuery
        ChatbotQuery.objects.create(source="public_swim", message="Is the pool open?", response_type="GPT",
                                    response="**Yes**, open till 9.\n\n- Lane swim<script>alert(1)</script>")
        response = self.get()
        self.assertContains(response, "<strong>Yes</strong>, open till 9.")
        self.assertContains(response, "<li>Lane swim")
        self.assertNotContains(response, "<script>alert")

    def test_chat_log_admin_shows_formatted_answer(self):
        from chatbot.models import ChatbotQuery
        chat = ChatbotQuery.objects.create(source="public_swim", message="Price?", response_type="GPT",
                                           response="It costs **€8**.")
        self.client.force_login(User.objects.filter(is_superuser=True).first()
                                or User.objects.create_superuser(email="root@tcsp.ie", password="pw"))
        change = self.client.get(reverse("settings:chatbot_chatbotquery_change", args=[chat.pk]))
        self.assertContains(change, "<strong>€8</strong>")
        changelist = self.client.get(reverse("settings:chatbot_chatbotquery_changelist"))
        self.assertContains(changelist, "It costs €8.")
        self.assertNotContains(changelist, "**€8**")


class ChatTopicTests(TestCase):
    """Sorting AI chat questions into topics for the dashboard."""

    def test_topics_by_keyword(self):
        from finances.views import _chat_topic
        cases = {
            "How much is public swim": "Prices & discounts",
            "is there a student rate": "Prices & discounts",
            "When are master classes on": "Masters, aqua & other classes",
            "Do I need a swim hat": "Pool, facilities & what to bring",
            "How do I rebook?": "Booking & changes",
            "what's the difference between beginner 1 and beginner 2": "Lesson levels & ages",
            "When is the next lane swim?": "Swim times & opening",
            "Hello": None,
        }
        for message, topic in cases.items():
            with self.subTest(message=message):
                self.assertEqual(_chat_topic(message), topic)

    def test_keywords_match_word_starts_only(self):
        from finances.views import _chat_topic
        # "page" must not count as "age", nor "separate" as "rate".
        self.assertIsNone(_chat_topic("separate page"))

    def test_summary_top_three(self):
        from chatbot.models import ChatbotQuery
        from finances.views import _chat_summary
        messages = (["How much is it"] * 3 + ["How do I book"] * 2 + ["Are there lockers"] * 2
                    + ["What time today"] + ["Hi"] * 2)
        for message in messages:
            ChatbotQuery.objects.create(source="public_swim", message=message, response_type="FAQ")
        ChatbotQuery.objects.create(source="public_swim", message="how much abuse", response_type="BLOCKED")
        summary = _chat_summary(ChatbotQuery.objects.all())
        self.assertEqual(summary["total"], 11)
        self.assertEqual(summary["faq_pct"], 91)  # 10 of 11; the blocked one is not an FAQ answer
        # Blocked messages are not sorted into topics.
        self.assertEqual([(t["name"], t["count"]) for t in summary["top"]],
                         [("Prices & discounts", 3), ("Booking & changes", 2),
                          ("Pool, facilities & what to bring", 2)])
        self.assertEqual([t["bar"] for t in summary["top"]], [100, 67, 67])
        self.assertEqual(summary["unsorted_pct"], 20)

    def test_no_questions_no_summary(self):
        from chatbot.models import ChatbotQuery
        from finances.views import _chat_summary
        self.assertIsNone(_chat_summary(ChatbotQuery.objects.all()))


class CheckoutFunnelTests(TestCase):
    """The live dashboard's "Checkouts finished" dial: families who reached the
    payment page this week, whether they paid, and how many needed another try."""

    @classmethod
    def setUpTestData(cls):
        from lessons_orders.models import Order as LessonOrder
        from swims_orders.models import Order as SwimOrder

        cls.manager = User.objects.create_user(email="manager@tcsp.ie", password="pw", first_name="M")
        cls.manager.is_staff = True
        cls.manager.save(update_fields=["is_staff"])
        cls.manager.groups.add(Group.objects.get_or_create(name="Manager")[0])

        def customer(name):
            return User.objects.create_user(email=f"{name}@example.com", password="pw", first_name=name)

        # Paid first time.
        SwimOrder.objects.create(user=customer("paid"), paid=True, amount="8.00")
        # Unpaid, then paid on a second try: one finished checkout, and a retry.
        retry = customer("retry")
        LessonOrder.objects.create(user=retry, amount="90.00")
        LessonOrder.objects.create(user=retry, paid=True, amount="90.00")
        # Two families who reached the payment page and never paid, one after two goes.
        SwimOrder.objects.create(user=customer("left"), amount="8.00")
        twice = customer("twice")
        SwimOrder.objects.create(user=twice, amount="8.00")
        SwimOrder.objects.create(user=twice, amount="8.00")
        # Not counted: a fully couponed order never reaches BOIPA, staff book for customers,
        # and last week's checkouts are outside this week.
        LessonOrder.objects.create(user=customer("free"), paid=True, amount="0.00")
        SwimOrder.objects.create(user=cls.manager, amount="8.00")
        old = SwimOrder.objects.create(user=customer("old"), amount="8.00")
        SwimOrder.objects.filter(pk=old.pk).update(created=timezone.now() - timedelta(days=8))

    def test_funnel_counts_families_not_orders(self):
        from finances.views import _activity_periods, _checkout_funnel
        _, _, (_, start, end) = _activity_periods()
        self.assertEqual(_checkout_funnel(start, end),
                         {"started": 4, "finished": 2, "retried": 1, "left": 2})

    def test_dial_is_on_the_live_dashboard_only(self):
        self.client.force_login(self.manager)
        dials = {d["title"]: d for d in self.client.get(reverse("finance:dashboard")).context["dials"]}
        dial = dials["Checkouts finished this week"]
        self.assertEqual((dial["value"], dial["max"], dial["pct"]), (2, 4, 50))
        self.assertEqual(dial["caption"], "families who reached payment · 1 needed more than one try · 2 left")
        strip = self.client.get(reverse("operations:index")).context["dial_strip"]
        self.assertNotIn("Checkouts finished this week", [d["title"] for d in strip])


class WhatsOnTodayTests(TestCase):
    """The brief "What's on today" on the staff home, Operations home and live dashboard."""

    @classmethod
    def setUpTestData(cls):
        from datetime import time

        from instructors.models import InstructorAssignment
        from schools.models import ScoCategory, ScoLessons, ScoProgram, ScoSchool
        from schools_bookings.models import ScoEnrollment, ScoTerm
        from swims.models import PriceVariant, PublicSwimCategory, PublicSwimProduct
        from swims_orders.models import Order as SwimOrder, OrderItem as SwimOrderItem

        cls.manager = User.objects.create_user(email="manager@tcsp.ie", password="pw", first_name="M")
        cls.manager.is_staff = True
        cls.manager.save(update_fields=["is_staff"])
        cls.manager.groups.add(Group.objects.get_or_create(name="Manager")[0])
        guardian = User.objects.create_user(email="parent@example.com", password="pw", first_name="P")
        instructor = User.objects.create_user(email="teacher@tcsp.ie", password="pw", first_name="T")

        today = timezone.localdate()
        cls.weekday = today.weekday()
        other_day = (cls.weekday + 1) % 7
        kids = [Swimling.objects.create(guardian=guardian, first_name=f"Kid{i}", last_name="T") for i in range(4)]

        swims = PublicSwimCategory.objects.create(name="Lane Swim", slug="lane-swim")
        session = PublicSwimProduct.objects.create(category=swims, day_of_week=cls.weekday, num_places=20,
                                                   start_time=time(7), end_time=time(8), available=True)
        PublicSwimProduct.objects.create(category=swims, day_of_week=other_day, num_places=50,
                                         start_time=time(9), end_time=time(10), available=True)
        variant = PriceVariant.objects.create(product=session, variant="Adult", price=8)
        order = SwimOrder.objects.create(user=guardian, product=session, booking=today, amount="16.00", paid=True)
        SwimOrderItem.objects.create(order=order, variant=variant, quantity=2)

        term = Term.objects.create(start_date=today - timedelta(days=10), end_date=today + timedelta(days=50))
        category = Category.objects.create(name="Beginners 1", program=Program.objects.create(name="P"))
        early = Product.objects.create(category=category, day_of_week=cls.weekday, num_places=5, active=True,
                                       start_time=time(16), end_time=time(16, 30))
        late = Product.objects.create(category=category, day_of_week=cls.weekday, num_places=5, active=True,
                                      start_time=time(18), end_time=time(18, 45))
        tomorrow = Product.objects.create(category=category, day_of_week=other_day, num_places=5, active=True,
                                          start_time=time(16), end_time=time(16, 30))
        for kid in kids[:3]:
            LessonEnrollment.objects.create(lesson=early, swimling=kid, term=term)
        LessonEnrollment.objects.create(lesson=late, swimling=kids[3], term=term)
        LessonEnrollment.objects.create(lesson=tomorrow, swimling=kids[0], term=term)
        InstructorAssignment.objects.create(instructor=instructor, lesson=early, term=term)

        school = ScoSchool.objects.create(name="St Mary's", sco_role_num="12345A")
        sco_category = ScoCategory.objects.create(name="Year 3", program=ScoProgram.objects.create(name="S"))
        sco_term = ScoTerm.objects.create(start_date=today - timedelta(days=5), end_date=today + timedelta(days=30),
                                          booking_start_date=today - timedelta(days=20),
                                          booking_end_date=today - timedelta(days=6), school=school)
        sco_lesson = ScoLessons.objects.create(category=sco_category, school=school, day_of_week=cls.weekday,
                                               start_time=time(9, 30), end_time=time(10, 30), num_places=30, active=True)
        for kid in kids[:2]:
            ScoEnrollment.objects.create(lesson=sco_lesson, swimling=kid, term=sco_term)

    def whats_on(self):
        from finances.views import _whats_on
        return _whats_on(timezone.localdate())

    def test_todays_swims_lessons_and_schools(self):
        from datetime import time
        on = self.whats_on()
        self.assertEqual([(s["start"], s["booked"], s["places"]) for s in on["swims"]], [(time(7), 2, 20)])
        lessons = on["lessons"]
        # Tomorrow's class is left out; the 18:00 class has nobody teaching it.
        self.assertEqual((lessons["classes"], lessons["swimmers"]), (2, 4))
        self.assertEqual([(u["start"], u["name"], u["swimmers"]) for u in lessons["unstaffed"]],
                         [(time(18), "Beginners 1", 1)])
        self.assertEqual((lessons["start"], lessons["end"]), (time(16), time(18, 45)))
        self.assertTrue(lessons["url"].endswith(f"?day={self.weekday}"))
        self.assertEqual([(s["name"], s["swimmers"]) for s in on["schools"]], [("St Mary's", 2)])
        self.assertFalse(on["empty"])

    def test_no_term_running(self):
        Term.objects.all().delete()
        on = self.whats_on()
        self.assertIsNone(on["lessons"])
        self.assertTrue(on["no_term"])

    def test_shown_on_all_three_pages(self):
        self.client.force_login(self.manager)
        for url in (reverse("dashboard:dashboard_home"), reverse("operations:index"), reverse("finance:dashboard")):
            response = self.client.get(url)
            self.assertContains(response, "What’s on today")
            self.assertContains(response, "1 with no instructor")
            self.assertContains(response, "St Mary&#x27;s")



class PeopleTilesTests(TestCase):
    """The live dashboard's counts of managers and other staff active, and of new
    customers who have gone on to add a swimmer."""

    @classmethod
    def setUpTestData(cls):
        from users.models import ActiveDay

        def staff(email, manager=False):
            user = User.objects.create_user(email=email, password="pw", first_name="S")
            user.is_staff = True
            user.save(update_fields=["is_staff"])
            if manager:
                user.groups.add(Group.objects.get_or_create(name="Manager")[0])
            return user

        cls.manager = staff("manager@tcsp.ie", manager=True)
        today = timezone.localdate()
        ActiveDay.objects.create(user=staff("manager2@tcsp.ie", manager=True), date=today)
        ActiveDay.objects.create(user=staff("desk@tcsp.ie"), date=today)
        ActiveDay.objects.create(user=staff("old@tcsp.ie"), date=today - timedelta(days=8))

        guardian = User.objects.create_user(email="parent@example.com", password="pw", first_name="P")
        Swimling.objects.create(guardian=guardian, first_name="Kid1", last_name="T")
        Swimling.objects.create(guardian=guardian, first_name="Kid2", last_name="T")
        User.objects.create_user(email="browser@example.com", password="pw", first_name="B")

    def tiles(self):
        self.client.force_login(self.manager)  # itself marks the manager active today
        response = self.client.get(reverse("finance:dashboard"))
        return {t["label"]: (t["today"], t["week"]) for t in response.context["tiles"]}

    def test_managers_and_other_staff_counted_apart(self):
        tiles = self.tiles()
        self.assertEqual(tiles["Managers active"][0], 2)
        self.assertEqual(tiles["Other staff active"][0], 1)
        self.assertNotIn("Staff logged in", tiles)

    def test_new_guardians_are_new_customers_with_a_swimmer(self):
        tiles = self.tiles()
        self.assertEqual(tiles["New customers"][0], 2)
        # Two swimmers on one account is still one guardian.
        self.assertEqual(tiles["New guardians"][0], 1)


class ChatRatingsDashboardTests(TestCase):
    """The live dashboard's "Answer ratings" card."""

    @classmethod
    def setUpTestData(cls):
        from chatbot.models import ChatbotQuery

        cls.manager = User.objects.create_user(email="manager@tcsp.ie", password="pw", first_name="M")
        cls.manager.is_staff = True
        cls.manager.save(update_fields=["is_staff"])
        cls.manager.groups.add(Group.objects.get_or_create(name="Manager")[0])

        def chat(kind, rating, message="Q", days_ago=0):
            ChatbotQuery.objects.create(source="public_swim", message=message, response="<p>An answer</p>",
                                        response_type=kind, rating=rating,
                                        rated_at=None if rating is None else timezone.now() - timedelta(days=days_ago))

        chat("FAQ", 1)
        chat("FAQ_HEDGED", -1, message="Is the pool 50 metres?")
        chat("GPT", 1)
        chat("GPT", 1)
        chat("GPT", None)  # not rated
        chat("GPT", -1, message="An old complaint", days_ago=40)  # outside the 30 days

    def test_ratings_split_by_where_the_answer_came_from(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("finance:dashboard"))
        ratings = response.context["chat_ratings"]
        self.assertEqual(ratings["all"], {"helpful": 3, "unhelpful": 1, "pct": 75})
        self.assertEqual(ratings["faq"], {"helpful": 1, "unhelpful": 1, "pct": 50})
        self.assertEqual(ratings["ai"], {"helpful": 2, "unhelpful": 0, "pct": 100})
        self.assertEqual([c["message"] for c in ratings["unhelpful"]], ["Is the pool 50 metres?"])
        self.assertContains(response, "Latest marked not helpful")

    def test_card_says_when_nothing_is_rated(self):
        from chatbot.models import ChatbotQuery
        ChatbotQuery.objects.update(rating=None, rated_at=None)
        self.client.force_login(self.manager)
        response = self.client.get(reverse("finance:dashboard"))
        self.assertIsNone(response.context["chat_ratings"])
        self.assertContains(response, "No answers rated yet")
