from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from import_export.admin import ImportExportMixin
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from schools_bookings.models import ScoEnrollment
from schools_bookings.resources import EnrollmentResource
from schools_bookings.filters import TermFilter, DayOfWeekFilter


@admin.register(ScoEnrollment)
class LessonEnrollmentAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = EnrollmentResource
    list_display = ['swimling', 'term', 'lesson', 'order_link']
    list_display_links = ('swimling',)
    raw_id_fields = ['swimling', 'lesson']
    search_fields = (
        'swimling__first_name',
        'swimling__last_name',
        'swimling__id',
        'lesson__name',
        'lesson__school__name',
        'term__school__name',
    )
    list_filter = [
        TermFilter,
        DayOfWeekFilter,
        ('lesson', RelatedDropdownFilter),
        ('lesson__category', RelatedDropdownFilter)
    ]
    list_per_page = 20

    def order_link(self, obj):
        if obj.order:
            link = reverse("admin:lessons_orders_order_change", args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', link, obj.order)
        return '-'

    order_link.short_description = 'Order'
