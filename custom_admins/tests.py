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
