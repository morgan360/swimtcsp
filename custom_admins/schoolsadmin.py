from django.contrib.admin import AdminSite
from django.contrib import admin
from schools.models import ScoLessons, ScoCategory, ScoProgram, ScoSchool
from schools_orders.models import Order
from schools_bookings.models import ScoTerm, ScoEnrollment
from users.models import Swimling
from .lessonsadmin import LessonEnrollmentAdmin, SwimlingAutocompleteAdmin
from import_export.admin import ImportExportMixin
from schools_bookings.resources import TermResource  # adjust if needed
from django.http import HttpResponse
import csv
from datetime import datetime

class ScoEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'swimling_name', 'guardian_name', 'guardian_email', 'lesson', 'term', 'school_name', 'created']
    list_filter = ['term', 'lesson__school', 'lesson', 'created']
    search_fields = [
        'swimling__first_name',
        'swimling__last_name',
        'swimling__guardian__first_name',
        'swimling__guardian__last_name',
        'swimling__guardian__email',
        'notes'
    ]
    readonly_fields = ['created', 'updated']
    list_select_related = ['swimling', 'swimling__guardian', 'lesson', 'lesson__school', 'term', 'order']
    actions = ['export_enrollments_csv']

    def swimling_name(self, obj):
        return f"{obj.swimling.first_name} {obj.swimling.last_name}"
    swimling_name.short_description = 'Swimling'
    swimling_name.admin_order_field = 'swimling__first_name'

    def guardian_name(self, obj):
        if obj.swimling.guardian:
            return f"{obj.swimling.guardian.first_name} {obj.swimling.guardian.last_name}"
        return "N/A"
    guardian_name.short_description = 'Guardian'
    guardian_name.admin_order_field = 'swimling__guardian__first_name'

    def guardian_email(self, obj):
        if obj.swimling.guardian:
            return obj.swimling.guardian.email
        return "N/A"
    guardian_email.short_description = 'Guardian Email'
    guardian_email.admin_order_field = 'swimling__guardian__email'

    def school_name(self, obj):
        if obj.lesson and obj.lesson.school:
            return obj.lesson.school.name
        return "N/A"
    school_name.short_description = 'School'
    school_name.admin_order_field = 'lesson__school__name'

    def export_enrollments_csv(self, request, queryset):
        """Export selected enrollments to CSV with guardian information"""
        response = HttpResponse(content_type='text/csv')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="school_enrollments_{timestamp}.csv"'

        writer = csv.writer(response)
        # Write header
        writer.writerow([
            'Enrollment ID',
            'Swimling First Name',
            'Swimling Last Name',
            'Guardian First Name',
            'Guardian Last Name',
            'Guardian Email',
            'Guardian Phone',
            'Lesson',
            'School',
            'Term Start Date',
            'Term End Date',
            'Created Date',
            'Order ID',
            'Notes'
        ])

        # Write data rows
        for enrollment in queryset.select_related(
            'swimling',
            'swimling__guardian',
            'lesson',
            'lesson__school',
            'term',
            'order'
        ):
            writer.writerow([
                enrollment.id,
                enrollment.swimling.first_name,
                enrollment.swimling.last_name,
                enrollment.swimling.guardian.first_name if enrollment.swimling.guardian else '',
                enrollment.swimling.guardian.last_name if enrollment.swimling.guardian else '',
                enrollment.swimling.guardian.email if enrollment.swimling.guardian else '',
                enrollment.swimling.guardian.phone_number if enrollment.swimling.guardian else '',
                enrollment.lesson.name if enrollment.lesson else '',
                enrollment.lesson.school.name if enrollment.lesson and enrollment.lesson.school else '',
                enrollment.term.start_date.strftime('%Y-%m-%d') if enrollment.term else '',
                enrollment.term.end_date.strftime('%Y-%m-%d') if enrollment.term else '',
                enrollment.created.strftime('%Y-%m-%d %H:%M:%S') if enrollment.created else '',
                enrollment.order.id if enrollment.order else '',
                enrollment.notes or ''
            ])

        return response

    export_enrollments_csv.short_description = "Export selected enrollments to CSV"

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
schools_admin_site.register(ScoEnrollment, ScoEnrollmentAdmin)
schools_admin_site.register(Swimling, SwimlingAutocompleteAdmin)
schools_admin_site.register(ScoLessons)
schools_admin_site.register(ScoCategory)
schools_admin_site.register(ScoProgram)
schools_admin_site.register(ScoSchool)
# schools_admin_site.register(ScoTerm)
schools_admin_site.register(Order)
schools_admin_site.register(ScoTerm, ScoTermAdmin)
