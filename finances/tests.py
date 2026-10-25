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
        dial = self.dials()["Attendance marked today"]
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

    def test_registers_taken_this_week(self):
        dial = self.dials()["Registers taken this week"]
        # The one Monday lesson is always due by today, and today's register for it is marked.
        self.assertEqual((dial["value"], dial["max"]), (1, 1))

    def test_registers_dial_ignores_registers_nobody_marked(self):
        from anseo.models import AttendanceEntry
        AttendanceEntry.objects.update(status=AttendanceEntry.UNKNOWN)
        dial = self.dials()["Registers taken this week"]
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
        self.assertEqual(titles, ["Today’s public swims", "Registers taken this week",
                                  "Attendance marked today", "This term’s lessons"])
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
