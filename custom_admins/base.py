"""Shared foundation for the TCSP admin panels.

The admin grew into ten separate AdminSite instances with no common base, so the
same improvement had to be made ten times and usually was not — "search fix on
lessons admin" appears three times in the history. Everything that should be true
of every panel lives here instead.

Two classes:

* ``TCSPAdminSite`` — a panel. Carries the stylesheet, the switcher shown on every
  page, and a ``has_permission`` that gates the panel on group membership.
* ``TCSPModelAdmin`` — a model within a panel. Supplies the changelist defaults
  (facet counts, sensible paging) and, most usefully, works out ``select_related``
  from ``list_display`` so foreign-key columns stop costing a query per row.
"""
from django.contrib import admin
from django.contrib.admin import AdminSite

# Canonical staff groups. These two names are unambiguous in the live data —
# unlike the instructor/guardian/school groups, which exist in several casings.
MANAGER_ONLY = ("Manager",)
MANAGER_AND_FULL_TIMER = ("Manager", "Full-Timer")

# Populated by register_panel() below; drives the switcher.
_PANELS = []


def register_panel(site):
    """Record a panel so every other panel can link to it."""
    _PANELS.append(site)
    return site


class TCSPAdminSite(AdminSite):
    """A TCSP admin panel.

    ``required_groups`` empty means any staff member. Superusers always pass.
    """

    required_groups: tuple = ()
    panel_icon = ""
    #: Where this panel is mounted. Kept separate from ``name`` (the URL
    #: namespace) so a panel can be renamed without breaking every reverse.
    panel_path = "/"

    def has_permission(self, request):
        user = request.user
        if not (user.is_active and user.is_staff):
            return False
        if user.is_superuser or not self.required_groups:
            return True
        return user.groups.filter(name__in=self.required_groups).exists()

    def each_context(self, request):
        context = super().each_context(request)
        context["custom_css"] = "css/tcsp_admin.css"
        # The switcher is rendered on every page, not just the index, because a
        # changelist is where staff actually are when they need another panel.
        context["tcsp_panels"] = [
            {
                "name": site.site_title,
                "icon": site.panel_icon,
                "url": site.panel_path,
                "current": site.name == self.name,
            }
            for site in _PANELS
            if site.has_permission(request)
        ]
        return context


class TCSPModelAdmin(admin.ModelAdmin):
    """Changelist defaults for every model in every panel."""

    show_facets = admin.ShowFacets.ALWAYS
    save_on_top = True
    list_per_page = 50
    empty_value_display = "—"

    #: Relations to follow that list_display cannot reveal on its own — a method
    #: like ``get_guardian`` that walks ``swimling.guardian`` needs naming here.
    list_select_related_extra: tuple = ()

    def get_list_select_related(self, request):
        """Follow every forward relation named in list_display.

        An explicit ``list_select_related`` on the subclass still wins; this only
        fills in the common case, where a column is simply a ForeignKey name.
        """
        configured = super().get_list_select_related(request)
        if configured:
            return configured

        names = list(self.list_select_related_extra)
        for column in self.get_list_display(request):
            if not isinstance(column, str):
                continue
            try:
                field = self.model._meta.get_field(column)
            except Exception:
                continue
            if field.is_relation and field.many_to_one:
                names.append(column)
        return names or False

    def get_search_results(self, request, queryset, search_term):
        return super().get_search_results(request, queryset, search_term)

    @property
    def search_help_text(self):
        """Say what the search box actually searches, rather than leaving staff to guess."""
        if not self.search_fields:
            return None
        labels = []
        for field in self.search_fields:
            cleaned = field.lstrip("^=@$").replace("__", " ").replace("_", " ")
            if cleaned not in labels:
                labels.append(cleaned)
        return "Searches: " + ", ".join(labels)
