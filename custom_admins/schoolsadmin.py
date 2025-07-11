from django.contrib.admin import AdminSite
from django.contrib import admin
from schools.models import ScoLessons, ScoCategory, ScoProgram, ScoSchool
from schools_orders.models import Order
from schools_bookings.models import ScoTerm, ScoEnrollment
from .lessonsadmin import LessonEnrollmentAdmin
from import_export.admin import ImportExportMixin
from schools_bookings.resources import TermResource  # adjust if needed


class ScoTermAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = TermResource
    list_display = ['id', 'is_active', 'start_date', 'end_date', 'booking_start_date', 'booking_end_date', 'school']
    list_filter = ['is_active', 'school']
    ordering = ['-start_date']


# ✅ Unregister from default admin (only needed if auto-registered elsewhere)
try:
    admin.site.unregister(ScoLessons)
except admin.sites.NotRegistered:
    pass

# ✅ Define your custom admin site
class SchoolsAdminSite(AdminSite):
    site_header = "🏫 Schools Admin"
    site_title = "Schools Admin Portal"
    index_title = "Manage School Programs and Bookings"

    def each_context(self, request):
        context = super().each_context(request)
        context["custom_css"] = "css/shared_admin.css"
        return context

# ✅ Create instance
schools_admin_site = SchoolsAdminSite(name='schoolsadmin')

# ✅ Register models to your custom site
schools_admin_site.register(ScoEnrollment, LessonEnrollmentAdmin)
schools_admin_site.register(ScoLessons)
schools_admin_site.register(ScoCategory)
schools_admin_site.register(ScoProgram)
schools_admin_site.register(ScoSchool)
# schools_admin_site.register(ScoTerm)
schools_admin_site.register(Order)
schools_admin_site.register(ScoTerm, ScoTermAdmin)
