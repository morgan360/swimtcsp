from django.contrib.admin import AdminSite
from django.contrib import admin
from anseo.models import AttendanceRoll, AttendanceEntry


class AttendanceAdminSite(AdminSite):
    site_header = "Attendance Admin"
    site_title = "Attendance Admin Portal"
    index_title = "Manage Attendance Records"


attendance_admin_site = AttendanceAdminSite(name='attendanceadmin')
@admin.register(AttendanceRoll, site=attendance_admin_site)
class AttendanceRollAdmin(admin.ModelAdmin):
    list_display = ('product', 'term', 'window_start', 'window_end', 'created_by', 'created_at')
    search_fields = ('product__name', 'term__label')
    list_filter = ('product', 'term')
    readonly_fields = ('created_by', 'created_at')


@admin.register(AttendanceEntry, site=attendance_admin_site)
class AttendanceEntryAdmin(admin.ModelAdmin):
    list_display = ('roll', 'enrollment', 'swimling_id', 'status', 'marked_by', 'marked_at')
    search_fields = ('enrollment__swimling__first_name', 'enrollment__swimling__last_name')
    list_filter = ('status', 'marked_at')
    readonly_fields = ('marked_at',)
