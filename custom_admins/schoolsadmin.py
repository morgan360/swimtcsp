from django.contrib.admin import AdminSite
from django.contrib import admin
from schools.models import ScoLessons, ScoCategory, ScoProgram, ScoSchool
from schools_orders.models import Order, OrderItem
from schools_bookings.models import ScoTerm, ScoEnrollment
from users.models import Swimling
from .lessonsadmin import LessonEnrollmentAdmin, SwimlingAutocompleteAdmin
from import_export.admin import ImportExportMixin
from schools_bookings.resources import TermResource  # adjust if needed
from django.http import HttpResponse
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
import csv
from datetime import datetime

class ScoEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'swimling_name', 'guardian_name', 'guardian_email', 'lesson', 'term', 'school_name', 'created']
    list_filter = [
        ('term', RelatedDropdownFilter),
        ('lesson__school', RelatedDropdownFilter),
        ('lesson', RelatedDropdownFilter),
        'created'
    ]
    autocomplete_fields = ['swimling']
    search_fields = [
        'swimling__first_name',
        'swimling__last_name',
        'swimling__guardian__first_name',
        'swimling__guardian__last_name',
        'swimling__guardian__email',
        'lesson__name',
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
                enrollment.swimling.guardian.mobile_phone if enrollment.swimling.guardian else '',
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

class ScoOrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ['product', 'term', 'swimling']


class ScoOrderAdmin(admin.ModelAdmin):
    """School orders.

    Registered bare until now, so the changelist showed only "Order 123" and
    you had to open each one to find out whose it was.
    """
    list_display = ['id', 'guardian', 'swimmers', 'school', 'amount', 'paid', 'created']
    list_display_links = ['id', 'guardian']
    list_filter = ['paid', ('school', RelatedDropdownFilter), 'created']
    search_fields = [
        'id',
        'user__first_name',
        'user__last_name',
        'user__email',
        'txId',
        'items__swimling__first_name',
        'items__swimling__last_name',
    ]
    readonly_fields = ['created', 'updated', 'txId', 'boipa_reconciled']
    # No date_hierarchy: it truncates dates in the database, which needs MySQL's
    # timezone tables loaded, and they are not. The 'created' list_filter covers
    # date filtering the way the rest of the admins here do.
    ordering = ['-created']
    inlines = [ScoOrderItemInline]

    def get_queryset(self, request):
        # guardian and swimmers are read for every row.
        return (
            super().get_queryset(request)
            .select_related('user', 'school')
            .prefetch_related('items__swimling')
        )

    def guardian(self, obj):
        if not obj.user:
            return "—"
        return obj.user.get_full_name() or obj.user.email
    guardian.short_description = 'Guardian'
    guardian.admin_order_field = 'user__last_name'

    def swimmers(self, obj):
        """The children the order was placed for — the thing you actually
        want to see without opening the order."""
        names = []
        for item in obj.items.all():
            swimling = item.swimling
            if not swimling:
                continue
            name = f"{swimling.first_name} {swimling.last_name or ''}".strip()
            if name and name not in names:
                names.append(name)
        return ', '.join(names) or "—"
    swimmers.short_description = 'Swimmer(s)'


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
schools_admin_site.register(Order, ScoOrderAdmin)
schools_admin_site.register(ScoTerm, ScoTermAdmin)
