from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from import_export.admin import ImportExportMixin
from schools.models import ScoLessons, ScoCategory
from schools_bookings.models import ScoTerm, ScoEnrollment
from .resources import EnrollmentResource, TermResource
from django.contrib.auth import get_user_model
import django_filters
from django.db import models
from utils.terms_utils import get_current_term, get_previous_term, get_next_term
from custom_admins.lessonsadmin import lessons_admin_site
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter
from django.utils.html import format_html
from django.urls import reverse
from enum import Enum
from datetime import time

# Enum for day of the week
class Weekday(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

    @classmethod
    def choices(cls):
        return [(key.value, key.name.title()) for key in cls]

# Filters for the lesson list
class TermFilter(admin.SimpleListFilter):
    title = 'Term Selection'
    parameter_name = 'term'

    def lookups(self, request, model_admin):
        # Ensure only active terms are fetched
        active_terms = ScoTerm.objects.filter(is_active=True).order_by('-start_date')
        term_list = [(term.id, f"{term} - {term.start_date}") for term in active_terms]
        print(term_list)  # Debug: Check output in the console
        return term_list

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(term__id=self.value())
        return queryset

class DayOfWeekFilter(SimpleListFilter):
    title = 'Day of Week'
    parameter_name = 'day_of_week'

    def lookups(self, request, model_admin):
        return Weekday.choices()

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(lesson__day_of_week=self.value())
        return queryset

class CategoryFilter(SimpleListFilter):
    title = 'Category'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        categories = ScoCategory.objects.annotate(
            name_id=models.functions.Concat('name', models.Value(' - '), 'id', output_field=models.CharField())
        ).values_list('name_id', 'id').distinct()
        return list(categories)

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(lesson__category_id=self.value())
        return queryset



@admin.register(ScoEnrollment)
class LessonEnrollmentAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = EnrollmentResource
    list_display = ['swimling', 'term', 'lesson', 'order_link']
    list_display_links = ('swimling',)
    raw_id_fields = ['swimling']
    # search_fields = ('swimling__first_name', 'swimling__last_name',)
    list_filter = [TermFilter, DayOfWeekFilter, ('lesson', RelatedDropdownFilter), ('lesson__category', RelatedDropdownFilter)]
    list_per_page = 20

    def order_link(self, obj):
        if obj.order:
            link = reverse("admin:lessons_orders_order_change", args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', link, obj.order)
        return '-'
    order_link.short_description = 'Order'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "term":
            kwargs["queryset"] = ScoTerm.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)




@admin.register(ScoTerm)
class TermAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = TermResource
    list_display = ['id', 'is_active', 'start_date', 'end_date', 'booking_start_date', 'booking_end_date', 'assessment_date', 'school', 'changed_by']
    exclude = ('changed_by',)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.changed_by = request.user
        super().save_model(request, obj, form, change)

# Register to Custom Admin Site
lessons_admin_site.register(ScoEnrollment, LessonEnrollmentAdmin)
lessons_admin_site.register(ScoTerm, TermAdmin)
