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
from django.contrib.auth import get_user_model
from django.urls import reverse

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
    #: Optional sub-sections of a big panel, shown as a second row of buttons:
    #: ``(slug, label, icon, app_labels)``. Each is the panel index filtered to
    #: those apps, so the models themselves stay where they are registered.
    sections: tuple = ()

    def has_permission(self, request):
        user = request.user
        if not (user.is_active and user.is_staff):
            return False
        if user.is_superuser or not self.required_groups:
            return True
        return user.groups.filter(name__in=self.required_groups).exists()

    def get_urls(self):
        from django.urls import path

        urls = [
            path("search/", self.admin_view(self.tcsp_search), name="tcsp_search"),
        ]
        if self.sections:
            urls.append(path("section/<slug:section>/",
                             self.admin_view(self.section_index), name="section"))
        return urls + super().get_urls()

    def section_index(self, request, section):
        """The panel index, cut down to one section's apps."""
        from django.http import Http404

        match = next((s for s in self.sections if s[0] == section), None)
        if match is None:
            raise Http404("No such section")
        _slug, label, _icon, app_labels = match
        app_list = [app for app in self.get_app_list(request)
                    if app["app_label"] in app_labels]
        return self.index(request, extra_context={"title": label, "app_list": app_list})

    def _current_section(self, request):
        """The section a page belongs to, read from its URL.

        Section pages are /<panel>/section/<slug>/; model pages are
        /<panel>/<app_label>/..., so a changelist lights up its section too.
        """
        rest = request.path[len(self.panel_path):] if request.path.startswith(self.panel_path) else ""
        parts = [p for p in rest.split("/") if p]
        if not parts:
            return None
        if parts[0] == "section" and len(parts) > 1:
            return parts[1]
        for slug, _label, _icon, app_labels in self.sections:
            if parts[0] in app_labels:
                return slug
        return None

    def tcsp_search(self, request):
        """Find a swimmer or a guardian without first choosing a panel.

        Desk staff answering the phone start from a name or a number, not from a
        model, and the records they need sit on different pages. Results always
        link into Operations, which every staff member can open.
        """
        from django.db.models import Q
        from django.shortcuts import render

        from users.models import Swimling

        term = (request.GET.get("q") or "").strip()
        swimlings, guardians = [], []
        if term:
            swimlings = list(
                Swimling.objects.select_related("guardian").filter(
                    Q(first_name__icontains=term)
                    | Q(last_name__icontains=term)
                    | Q(guardian__email__icontains=term)
                    | Q(guardian__last_name__icontains=term)
                ).order_by("last_name", "first_name")[:25]
            )
            User = get_user_model()
            guardians = list(
                User.objects.filter(
                    Q(email__icontains=term)
                    | Q(first_name__icontains=term)
                    | Q(last_name__icontains=term)
                    | Q(mobile_phone__icontains=term)
                ).order_by("last_name", "first_name")[:25]
            )

        return render(request, "admin/tcsp_search.html", {
            **self.each_context(request),
            "title": f"Search results for “{term}”" if term else "Search",
            "query": term,
            "swimlings": swimlings,
            "guardians": guardians,
        })

    def each_context(self, request):
        context = super().each_context(request)
        context["custom_css"] = "css/tcsp_admin.css"
        context["tcsp_search_url"] = reverse(f"{self.name}:tcsp_search")
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
        if self.sections:
            current = self._current_section(request)
            context["tcsp_sections"] = [
                {
                    "name": label,
                    "icon": icon,
                    "url": reverse(f"{self.name}:section", args=[slug]),
                    "current": slug == current,
                }
                for slug, label, icon, _apps in self.sections
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
