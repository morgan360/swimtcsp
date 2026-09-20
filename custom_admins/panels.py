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
from custom_admins.base import MANAGER_ONLY, TCSPAdminSite, register_panel


class OperationsAdminSite(TCSPAdminSite):
    site_header = "🏊 TCSP Operations"
    site_title = "Operations"
    index_title = "Lessons, swims, schools, attendance and instructors"
    panel_icon = "🏊"
    panel_path = "/operations/"
    required_groups = ()  # any staff member


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
