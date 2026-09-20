from django.contrib.admin import AdminSite
from django.contrib import admin
from anseo.models import AttendanceRoll, AttendanceEntry
from utils.admin_filters import SearchableRelatedDropdownFilter

from custom_admins.panels import operations_site
from custom_admins.base import TCSPModelAdmin




# Panel consolidation: this name now points at the shared panel.
attendance_admin_site = operations_site
@admin.register(AttendanceRoll, site=attendance_admin_site)
class AttendanceRollAdmin(TCSPModelAdmin):
    list_display = ('product', 'term', 'window_start', 'window_end', 'created_by', 'created_at')
    search_fields = ('product__name', 'term__label')
    list_filter = [('product', SearchableRelatedDropdownFilter), ('term', SearchableRelatedDropdownFilter)]
    readonly_fields = ('created_by', 'created_at')


@admin.register(AttendanceEntry, site=attendance_admin_site)
class AttendanceEntryAdmin(TCSPModelAdmin):
    list_display = ('roll', 'enrollment', 'swimling_id', 'status', 'marked_by', 'marked_at')
    search_fields = ('enrollment__swimling__first_name', 'enrollment__swimling__last_name')
    list_filter = ('status', 'marked_at')
    readonly_fields = ('marked_at',)
