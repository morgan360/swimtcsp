# custom_admins/lessonsadmin.py

from import_export.admin import ImportExportMixin
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from schools_bookings.models import ScoEnrollment
from schools_bookings.resources import EnrollmentResource  # adjust path if needed
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
from django.contrib.admin import SimpleListFilter


class LessonEnrollmentAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = EnrollmentResource
    list_display = ['swimling', 'term', 'lesson', 'order_link']
    list_display_links = ('swimling',)
    raw_id_fields = ['swimling']
    list_filter = [
        ('term', RelatedDropdownFilter),
        ('lesson', RelatedDropdownFilter),
        ('lesson__category', RelatedDropdownFilter),
    ]
    list_per_page = 20

    def order_link(self, obj):
        if obj.order:
            link = reverse("admin:lessons_orders_order_change", args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', link, obj.order)
        return '-'
    order_link.short_description = 'Order'
from django.contrib.admin import AdminSite

class LessonsAdminSite(AdminSite):
    site_header = "🏫 Lessons Admin"
    site_title = "Lessons Admin Portal"
    index_title = "Manage Lesson Programs and Terms"

    def each_context(self, request):
        context = super().each_context(request)
        context["custom_css"] = "css/shared_admin.css"
        return context

# ✅ Exported instance
lessons_admin_site = LessonsAdminSite(name='lessonsadmin')
