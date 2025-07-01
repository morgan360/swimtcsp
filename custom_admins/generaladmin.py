from django.contrib.admin import AdminSite, TabularInline, ModelAdmin
from navigation.models import MenuGroup, MenuItem
from timetable.models import TimetableOverride
from waiting_list.models import WaitingList  # ✅ Import your model
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
    extra = 1
    can_delete = True
    show_change_link = True
    classes = ['collapse']

# ✅ Custom MenuGroup admin with inlines
class MenuGroupAdmin(ModelAdmin):
    list_display = ['name']
    inlines = [MenuItemInline]

# ✅ Optional: customize WaitingList admin
class WaitingListAdmin(ModelAdmin):
    list_display = ['swimling', 'product', 'user', 'is_notified', 'notification_date']
    list_filter = ['is_notified']
    search_fields = ['swimling__name', 'user__email', 'product__name']

# ✅ Register models to general admin site
general_admin_site.register(MenuGroup, MenuGroupAdmin)
general_admin_site.register(MenuItem)
general_admin_site.register(TimetableOverride)
general_admin_site.register(WaitingList, WaitingListAdmin)  # ✅ Registered here
