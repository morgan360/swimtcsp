"""The three TCSP admin panels.

Replaces the nine single-purpose AdminSite instances. Models are registered onto
these from the app admin modules, exactly as before — only the target changed.

    Operations  /operations/       every staff member
    Finance     /finance/          Manager, Full-Timer, superusers
    Settings    /settings-admin/   Manager, superusers

Stock ``admin.site`` stays mounted at /admin/ for superusers: it is where
third-party models (allauth, sites) surface and where anything not deliberately
placed will appear.

Finance keeps its own class in ``financeadmin`` because it carries ten custom
URLs for the revenue and reconciliation dashboards; it is registered as a panel
from here so the switcher lists all three in a sensible order.
"""
from django.urls import reverse

from custom_admins.base import MANAGER_ONLY, TCSPAdminSite, register_panel


class OperationsAdminSite(TCSPAdminSite):
    site_header = "🏊 TCSP Operations"
    site_title = "Operations"
    index_title = "Lessons, swims, schools, attendance and instructors"
    panel_icon = "🏊"
    panel_path = "/operations/"
    required_groups = ()  # any staff member
    # Operations holds most of the models, so it is split into the areas staff
    # used to have as separate panels. Every registered app should appear in
    # one section — the tests check — or its models are only on "All".
    sections = (
        ("lessons", "Lessons", "📚", ("lessons", "lessons_bookings", "waiting_list")),
        ("swims", "Swims", "🏊", ("swims",)),
        ("timetable", "Timetable & closures", "📅", ("timetable",)),
        ("schools", "Schools", "🏫", ("schools", "schools_bookings")),
        ("members", "Members", "👪", ("users",)),
        ("instructors", "Instructors & attendance", "📋", ("instructors", "anseo", "progress")),
    )
    index_template = "admin/operations/index.html"

    def index(self, request, extra_context=None):
        """The panel's home, with a strip of today's dials across the top.

        Section pages reuse ``index`` with their own context and go without it,
        so the strip is on the one page staff land on rather than on every list.
        Only figures any staff member may see: no money, which stays in Finance.
        """
        if extra_context is None:
            from django.utils.timezone import localtime, now

            from custom_admins.financeadmin import finance_admin_site
            from finances.views import _live_dials, _whats_on

            today = localtime(now()).date()
            live = _live_dials(today)
            extra_context = {
                "dial_strip": [live[key] for key in ("swims", "registers", "attendance", "term") if live[key]],
                "whats_on": _whats_on(today),
                "live_dashboard_url": (reverse("finance:dashboard")
                                       if finance_admin_site.has_permission(request) else None),
            }
        return super().index(request, extra_context)


class SettingsAdminSite(TCSPAdminSite):
    site_header = "⚙️ TCSP Settings"
    site_title = "Settings"
    index_title = "People, terms, navigation and site configuration"
    panel_icon = "⚙️"
    panel_path = "/settings-admin/"
    required_groups = MANAGER_ONLY


operations_site = register_panel(OperationsAdminSite(name="operations"))

# Imported after Operations so the switcher reads Operations, Finance, Settings.
from custom_admins.financeadmin import finance_admin_site as finance_site  # noqa: E402

register_panel(finance_site)

settings_site = register_panel(SettingsAdminSite(name="settings"))
