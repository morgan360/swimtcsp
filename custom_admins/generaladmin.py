from django.contrib.admin import AdminSite, TabularInline, ModelAdmin
from navigation.models import MenuGroup, MenuItem
from timetable.models import TimetableOverride
from django.contrib import admin

class GeneralAdminSite(AdminSite):
    site_header = "⚙️ General Admin"
    site_title = "General Admin Portal"
    index_title = "Manage Navigation, Timetables, and Settings"

    def each_context(self, request):
        context = super().each_context(request)
        context["custom_css"] = "css/shared_admin.css"
        return context


general_admin_site = GeneralAdminSite(name='generaladmin')

# ✅ Inline: show MenuItems under MenuGroup
class MenuItemInline(admin.StackedInline):
    model = MenuItem
    extra = 1  # one blank entry shown by default
    can_delete = True
    show_change_link = True  # optional: link to detail view
    classes = ['collapse']  # optional: adds collapse toggle to inline block


# ✅ Custom MenuGroup admin with inlines
class MenuGroupAdmin(ModelAdmin):
    list_display = ['name']
    inlines = [MenuItemInline]


# ✅ Register models to general admin site
general_admin_site.register(MenuGroup, MenuGroupAdmin)
general_admin_site.register(MenuItem)  # optional: remove if you only want inline editing
general_admin_site.register(TimetableOverride)
