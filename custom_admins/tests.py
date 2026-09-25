"""Access rules and health of the three admin panels."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

import core.urls  # noqa: F401  — registers the panels' models
from custom_admins.panels import finance_site, operations_site, settings_site

User = get_user_model()

PANELS = {"operations": operations_site, "finance": finance_site, "settings": settings_site}


def make_user(email, groups=(), staff=True, superuser=False):
    user = User.objects.create_user(email=email, password="pw", first_name=email.split("@")[0])
    user.is_staff = staff
    user.is_superuser = superuser
    user.save(update_fields=["is_staff", "is_superuser"])
    for name in groups:
        user.groups.add(Group.objects.get_or_create(name=name)[0])
    return user


class PanelAccessTests(TestCase):
    """Who may open which panel.

    Every staff member could previously reach every panel, including finance.
    """

    @classmethod
    def setUpTestData(cls):
        cls.desk = make_user("desk@tcsp.ie", ["Desk", "instructor"])
        cls.full_timer = make_user("full@tcsp.ie", ["Full-Timer"])
        cls.manager = make_user("manager@tcsp.ie", ["Manager"])
        cls.superuser = make_user("root@tcsp.ie", superuser=True)
        cls.customer = make_user("parent@example.com", ["Guardian"], staff=False)

    def assert_access(self, user, expected):
        self.client.force_login(user)
        for name, allowed in expected.items():
            with self.subTest(user=user.email, panel=name):
                response = self.client.get(reverse(f"{name}:index"))
                if allowed:
                    self.assertEqual(response.status_code, 200)
                else:
                    self.assertNotEqual(
                        response.status_code, 200,
                        f"{user.email} should not reach the {name} panel")

    def test_desk_staff_reach_operations_only(self):
        self.assert_access(self.desk, {"operations": True, "finance": False, "settings": False})

    def test_full_timers_reach_operations_and_finance(self):
        self.assert_access(self.full_timer, {"operations": True, "finance": True, "settings": False})

    def test_managers_reach_everything(self):
        self.assert_access(self.manager, {"operations": True, "finance": True, "settings": True})

    def test_superusers_reach_everything(self):
        self.assert_access(self.superuser, {"operations": True, "finance": True, "settings": True})

    def test_customers_reach_nothing(self):
        self.assert_access(self.customer, {"operations": False, "finance": False, "settings": False})

    def test_anonymous_visitors_reach_nothing(self):
        for name in PANELS:
            with self.subTest(panel=name):
                self.assertNotEqual(self.client.get(reverse(f"{name}:index")).status_code, 200)


class PanelChangelistTests(TestCase):
    """Every registered changelist must render.

    One loop over the whole surface catches a broken list_display callable or a
    bad select_related anywhere, which is what a per-panel spot check misses.
    """

    @classmethod
    def setUpTestData(cls):
        cls.superuser = make_user("root@tcsp.ie", superuser=True)

    def test_every_changelist_renders(self):
        self.client.force_login(self.superuser)
        for panel, site in PANELS.items():
            for model in site._registry:
                meta = model._meta
                url = reverse(f"{panel}:{meta.app_label}_{meta.model_name}_changelist")
                with self.subTest(panel=panel, model=meta.label):
                    self.assertEqual(self.client.get(url).status_code, 200, f"{panel}: {meta.label}")


class RetiredPanelRedirectTests(TestCase):
    """The nine old panel URLs are bookmarked; they must not 404."""

    RETIRED = {
        "/lessonsadmin/": "/operations/",
        "/swimsadmin/": "/operations/",
        "/schoolsadmin/": "/operations/",
        "/instructorsadmin/": "/operations/",
        "/attendanceadmin/": "/operations/",
        "/generaladmin/": "/settings-admin/",
        "/usersadmin/": "/settings-admin/",
        "/couponsadmin/": "/finance/",
        "/finance-admin/": "/finance/",
    }

    def test_old_panel_roots_redirect(self):
        for old, new in self.RETIRED.items():
            with self.subTest(old=old):
                response = self.client.get(old)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response["Location"], new)

    def test_old_deep_links_keep_their_tail_and_query(self):
        response = self.client.get("/lessonsadmin/lessons_bookings/lessonenrollment/?term__id__exact=3")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            "/operations/lessons_bookings/lessonenrollment/?term__id__exact=3")


class GuardianLookupTests(TestCase):
    """Desk staff look guardians up by phone; they must not be able to edit them."""

    @classmethod
    def setUpTestData(cls):
        cls.desk = make_user("desk@tcsp.ie", ["Desk"])
        cls.guardian = make_user("parent@example.com", ["Guardian"], staff=False)

    def test_desk_staff_can_view_a_guardian(self):
        self.client.force_login(self.desk)
        url = reverse("operations:users_user_change", args=[self.guardian.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_desk_staff_cannot_edit_a_guardian(self):
        self.client.force_login(self.desk)
        response = self.client.post(
            reverse("operations:users_user_change", args=[self.guardian.pk]),
            {"email": "changed@example.com", "first_name": "Changed"})
        self.guardian.refresh_from_db()
        self.assertEqual(self.guardian.email, "parent@example.com")
        self.assertIn(response.status_code, (302, 403))

    def test_desk_staff_cannot_reach_the_editable_user_admin(self):
        self.client.force_login(self.desk)
        self.assertNotEqual(
            self.client.get(reverse("settings:users_user_changelist")).status_code, 200)


class PanelSwitcherTests(TestCase):
    """The switcher appears on every page and lists only reachable panels.

    It previously existed only on index pages, so from a changelist — where
    staff spend their time — there was no way to reach another panel.
    """

    @classmethod
    def setUpTestData(cls):
        cls.desk = make_user("desk@tcsp.ie", ["Desk"])
        cls.manager = make_user("manager@tcsp.ie", ["Manager"])
        # Reaching a changelist needs Django model permissions as well as the
        # panel's own check, and those are granted per group in production.
        cls.root = make_user("root@tcsp.ie", superuser=True)

    def test_desk_staff_see_only_operations(self):
        self.client.force_login(self.desk)
        html = self.client.get(reverse("operations:index")).content.decode()
        self.assertIn('href="/operations/"', html)
        self.assertNotIn('href="/finance/"', html)
        self.assertNotIn('href="/settings-admin/"', html)

    def test_managers_see_all_three(self):
        self.client.force_login(self.manager)
        html = self.client.get(reverse("operations:index")).content.decode()
        for url in ("/operations/", "/finance/", "/settings-admin/"):
            self.assertIn(f'href="{url}"', html)

    def test_switcher_is_present_on_a_changelist_not_just_the_index(self):
        self.client.force_login(self.root)
        html = self.client.get(reverse("operations:users_swimling_changelist")).content.decode()
        self.assertIn('class="tcsp-panels"', html)
        self.assertIn('href="/finance/"', html)


class OperationsSectionTests(TestCase):
    """Operations split into sections, so Lessons, Swims and Schools are one click away."""

    @classmethod
    def setUpTestData(cls):
        cls.root = make_user("root@tcsp.ie", superuser=True)

    def test_every_operations_app_belongs_to_a_section(self):
        # An app left out would only be reachable from the unfiltered index.
        covered = {label for *_rest, apps in operations_site.sections for label in apps}
        registered = {model._meta.app_label for model in operations_site._registry}
        self.assertEqual(registered - covered, set())

    def test_section_shows_only_its_own_apps(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse("operations:section", args=["swims"]))
        self.assertEqual(response.status_code, 200)
        labels = {app["app_label"] for app in response.context["app_list"]}
        self.assertEqual(labels, {"swims"})

    def test_unknown_section_is_404(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse("operations:section", args=["nope"]))
        self.assertEqual(response.status_code, 404)

    def test_changelist_highlights_its_section(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse("operations:lessons_bookings_term_changelist"))
        current = [s["name"] for s in response.context["tcsp_sections"] if s["current"]]
        self.assertEqual(current, ["Lessons"])

    def test_other_panels_have_no_section_row(self):
        self.client.force_login(self.root)
        html = self.client.get(reverse("finance:index")).content.decode()
        self.assertNotIn('class="tcsp-sections"', html)

    def test_refunds_are_on_finance_not_operations(self):
        from boipa.models import Refund
        self.assertIn(Refund, finance_site._registry)
        self.assertNotIn(Refund, operations_site._registry)


class ManagementPageTests(TestCase):
    """/management/ was linked from every admin index page and raised NoReverseMatch."""

    def test_management_page_loads(self):
        user = make_user("manager@tcsp.ie", ["Manager"])
        self.client.force_login(user)
        self.assertEqual(self.client.get("/management/").status_code, 200)


class DangerousActionTests(TestCase):
    """Actions that move money or overwrite tables must ask first."""

    @classmethod
    def setUpTestData(cls):
        cls.root = make_user("root@tcsp.ie", superuser=True)

    def setUp(self):
        self.client.force_login(self.root)

    def test_refund_shows_a_confirmation_page_before_refunding(self):
        from lessons_orders.models import Order

        order = Order.objects.create(user=self.root, amount=50, paid=True, txId="TX1")
        response = self.client.post(
            reverse("finance:lessons_orders_order_changelist"),
            {"action": "refund_orders", "_selected_action": [str(order.pk)]})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot be undone")
        order.refresh_from_db()
        self.assertNotEqual(order.payment_status, "refunded")

    def test_sync_terms_shows_a_confirmation_page(self):
        from lessons_bookings.models import Term

        term = Term.objects.create(
            start_date="2026-01-05", end_date="2026-03-27",
            rebooking_date="2025-12-01", booking_date="2025-12-08")
        response = self.client.post(
            reverse("operations:lessons_bookings_term_changelist"),
            {"action": "sync_terms_now", "_selected_action": [str(term.pk)]})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "rewrites all")


class PaymentRecordsAreReadOnlyTests(TestCase):
    """Gateway records were fully editable; staff could rewrite a txId."""

    def test_notification_admins_refuse_edits(self):
        from django.contrib import admin as dj_admin

        from boipa.models import (LessonOrderPaymentNotification,
                                  SchoolOrderPaymentNotification,
                                  SwimOrderPaymentNotification)
        request = type("R", (), {"user": make_user("root@tcsp.ie", superuser=True)})()
        for model in (SwimOrderPaymentNotification, LessonOrderPaymentNotification,
                      SchoolOrderPaymentNotification):
            with self.subTest(model=model.__name__):
                ma = dj_admin.site._registry[model]
                self.assertFalse(ma.has_add_permission(request))
                self.assertFalse(ma.has_change_permission(request))
                self.assertFalse(ma.has_delete_permission(request))
                self.assertIn("txId", ma.get_readonly_fields(request))
                self.assertIn("amount", ma.get_readonly_fields(request))


class StaffFlagsAreSuperuserOnlyTests(TestCase):
    """The user admin was a privilege-escalation route."""

    def test_non_superuser_cannot_edit_staff_flags(self):
        from django.contrib import admin as dj_admin

        from custom_admins.panels import settings_site
        manager = make_user("manager@tcsp.ie", ["Manager"])
        ma = settings_site._registry[User]
        readonly = ma.get_readonly_fields(type("R", (), {"user": manager})())
        for field in ("is_staff", "is_superuser", "groups"):
            self.assertIn(field, readonly)

    def test_superuser_can_edit_staff_flags(self):
        from custom_admins.panels import settings_site
        root = make_user("root@tcsp.ie", superuser=True)
        ma = settings_site._registry[User]
        readonly = ma.get_readonly_fields(type("R", (), {"user": root})())
        self.assertNotIn("is_staff", readonly)


class ChangelistQueryCountTests(TestCase):
    """Query counts must not grow with the number of rows.

    The waiting list ran two extra queries per row — an EXISTS for the sibling
    column and another for the sibling filter — on top of four guardian columns.
    """

    @classmethod
    def setUpTestData(cls):
        from datetime import date, time, timedelta

        from lessons.models import Category, Product, Program
        from users.models import Swimling
        from waiting_list.models import WaitingList

        cls.root = make_user("root@tcsp.ie", superuser=True)
        program = Program.objects.create(name="Public Lessons")
        category = Category.objects.create(name="Beginners", slug="beginners", program=program)
        cls.product = Product.objects.create(
            category=category, day_of_week=0,
            start_time=time(17, 0), end_time=time(17, 45), active=True)

        cls.guardians = []
        for i in range(6):
            guardian = make_user(f"g{i}@example.com", ["Guardian"], staff=False)
            swimling = Swimling.objects.create(
                first_name=f"Child{i}", last_name="Test", guardian=guardian,
                dob=date.today() - timedelta(days=3000))
            WaitingList.objects.create(swimling=swimling, product=cls.product)
            cls.guardians.append(guardian)

    def test_waiting_list_does_not_scale_queries_with_rows(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        self.client.force_login(self.root)
        url = reverse("operations:waiting_list_waitinglist_changelist")

        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(self.client.get(url).status_code, 200)
        six_rows = len(ctx.captured_queries)

        from waiting_list.models import WaitingList
        keep = list(WaitingList.objects.values_list("pk", flat=True))[:1]
        WaitingList.objects.exclude(pk__in=keep).delete()

        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(self.client.get(url).status_code, 200)
        one_row = len(ctx.captured_queries)

        self.assertLessEqual(
            six_rows - one_row, 1,
            f"query count grew from {one_row} to {six_rows} for five more rows — "
            "something is querying per row")


class AdminMenuItemTests(TestCase):
    """The public nav is database-driven and fails silently.

    MenuItem.resolve_url() returns "#" when reverse() fails, so a stale url_name
    becomes a link that does nothing rather than an error. Renaming the admin
    namespaces killed six of them.
    """

    RETIRED = [
        "swimsadmin:index", "lessonsadmin:index", "schoolsadmin:index",
        "instructorsadmin:index", "usersadmin:index", "generaladmin:index",
        "couponsadmin:index", "attendanceadmin:index", "financeadmin:index",
    ]

    def test_panel_namespaces_the_menu_points_at_resolve(self):
        from navigation.models import MenuGroup, MenuItem

        group = MenuGroup.objects.create(name="Admin")
        for url_name in ("operations:index", "finance:index", "settings:index"):
            item = MenuItem.objects.create(group=group, label=url_name, url_name=url_name)
            with self.subTest(url_name=url_name):
                self.assertNotEqual(
                    item.resolve_url(), "#",
                    f"{url_name} does not reverse, so the menu item would be a dead link")

    def test_retired_namespaces_no_longer_resolve(self):
        """If one of these ever reverses again, a panel was resurrected by accident."""
        from django.urls import NoReverseMatch, reverse

        for url_name in self.RETIRED:
            with self.subTest(url_name=url_name):
                with self.assertRaises(NoReverseMatch):
                    reverse(url_name)


class DrawerMenuVisibilityTests(TestCase):
    """Superusers must see every menu item they can actually open.

    required_groups was checked strictly against user.groups, so a superuser who
    is not in the named group lost the link even though the panel admits them.
    """

    def _menu_labels(self, user):
        from django.template import Context, Template

        request = type("R", (), {"user": user})()
        template = Template("{% load navigation_tags %}{% drawer_menu as menu %}"
                            "{% for group, items in menu.items %}"
                            "{% for i in items %}{{ i.label }}|{% endfor %}{% endfor %}")
        return template.render(Context({"request": request})).split("|")

    def test_superuser_sees_an_item_gated_on_a_group_they_lack(self):
        from django.contrib.auth.models import Group

        from navigation.models import MenuGroup, MenuItem

        menu_group = MenuGroup.objects.create(name="Admin")
        item = MenuItem.objects.create(
            group=menu_group, label="Settings", url_name="settings:index",
            requires_login=True, requires_staff=True)
        item.required_groups.add(Group.objects.create(name="Manager"))

        # A superuser in 'administrator' but not 'Manager' — the real shape of
        # this site's superuser accounts.
        root = make_user("root@tcsp.ie", ["administrator"], superuser=True)
        self.assertIn("Settings", self._menu_labels(root))

    def test_staff_without_the_group_still_do_not_see_it(self):
        from django.contrib.auth.models import Group

        from navigation.models import MenuGroup, MenuItem

        menu_group = MenuGroup.objects.create(name="Admin")
        item = MenuItem.objects.create(
            group=menu_group, label="Settings", url_name="settings:index",
            requires_login=True, requires_staff=True)
        item.required_groups.add(Group.objects.create(name="Manager"))

        desk = make_user("desk@tcsp.ie", ["Desk"])
        self.assertNotIn("Settings", self._menu_labels(desk))


class HeaderSearchTests(TestCase):
    """One lookup box, so finding a person does not start with picking a panel."""

    @classmethod
    def setUpTestData(cls):
        from datetime import date, timedelta

        from users.models import Swimling

        cls.desk = make_user("desk@tcsp.ie", ["Desk"])
        cls.guardian = make_user("bridget.okeeffe@example.com", ["Guardian"], staff=False)
        cls.guardian.first_name, cls.guardian.last_name = "Bridget", "O'Keeffe"
        cls.guardian.save()
        cls.swimling = Swimling.objects.create(
            first_name="Saoirse", last_name="O'Keeffe", guardian=cls.guardian,
            dob=date.today() - timedelta(days=3000))

    def _search(self, q, panel="operations"):
        self.client.force_login(self.desk)
        return self.client.get(reverse(f"{panel}:tcsp_search"), {"q": q})

    def test_finds_a_child_by_first_name(self):
        response = self._search("Saoirse")
        self.assertContains(response, "Saoirse")
        self.assertContains(response, "bridget.okeeffe@example.com")

    def test_finds_a_child_by_the_parents_email(self):
        self.assertContains(self._search("bridget.okeeffe@example"), "Saoirse")

    def test_finds_a_guardian_by_surname(self):
        self.assertContains(self._search("O'Keeffe"), "Bridget")

    def test_search_exists_on_every_panel(self):
        root = make_user("root@tcsp.ie", superuser=True)
        self.client.force_login(root)
        for panel in ("operations", "finance", "settings"):
            with self.subTest(panel=panel):
                self.assertEqual(
                    self.client.get(reverse(f"{panel}:tcsp_search"), {"q": "Saoirse"}).status_code, 200)

    def test_desk_staff_are_not_offered_a_panel_they_cannot_open(self):
        self.client.force_login(self.desk)
        self.assertNotEqual(self.client.get(reverse("finance:tcsp_search")).status_code, 200)

    def test_empty_search_renders_a_prompt_not_an_error(self):
        self.client.force_login(self.desk)
        response = self.client.get(reverse("operations:tcsp_search"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Type a child")


class HeaderRendersCleanlyTests(TestCase):
    """Django's {# #} comment is single-line only.

    A multi-line one is not a comment at all — it renders as literal text, which
    is how a note about the search box ended up printed across the admin header.
    """

    @classmethod
    def setUpTestData(cls):
        cls.root = make_user("root@tcsp.ie", superuser=True)

    def test_no_raw_template_syntax_reaches_the_page(self):
        self.client.force_login(self.root)
        for panel in ("operations", "finance", "settings"):
            html = self.client.get(reverse(f"{panel}:index")).content.decode()
            with self.subTest(panel=panel):
                for token in ("{#", "#}", "{%", "%}"):
                    self.assertNotIn(token, html, f"raw template syntax {token!r} rendered into the page")

    def test_header_carries_the_search_box_and_switcher(self):
        self.client.force_login(self.root)
        html = self.client.get(reverse("operations:index")).content.decode()
        self.assertIn('class="tcsp-search"', html)
        self.assertIn('class="tcsp-panels"', html)


class AdminPageTitleTests(TestCase):
    """Every admin page needs a browser-tab title.

    Replacing admin/base_site.html wholesale dropped Django's {% block title %},
    so every panel page rendered <title></title> and staff with several tabs
    open could not tell them apart.
    """

    @classmethod
    def setUpTestData(cls):
        cls.root = make_user("root@tcsp.ie", superuser=True)

    def test_panel_pages_have_a_title(self):
        self.client.force_login(self.root)
        for panel, site in PANELS.items():
            html = self.client.get(reverse(f"{panel}:index")).content.decode()
            with self.subTest(panel=panel):
                self.assertNotIn("<title></title>", html)
                self.assertIn(site.site_title, html)

    def test_a_changelist_has_a_title(self):
        self.client.force_login(self.root)
        html = self.client.get(reverse("operations:users_swimling_changelist")).content.decode()
        self.assertNotIn("<title></title>", html)

    def test_the_login_page_has_a_title_and_a_theme_toggle(self):
        """Anonymous visitors have no user tools, so the toggle lives in branding."""
        html = self.client.get(reverse("operations:login")).content.decode()
        self.assertNotIn("<title></title>", html)
        self.assertIn("theme-toggle", html)
