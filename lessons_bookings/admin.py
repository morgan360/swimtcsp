from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from import_export.admin import ImportExportMixin
from .models import Term, LessonAssignment, LessonEnrollment
from lessons.models import Product, Category
from .resources import EnrollmentResource, TermResource
from django.contrib.auth import get_user_model
import django_filters
from utils.terms_utils import get_current_term, get_previous_term, get_next_term
from custom_admins.lessonsadmin import lessons_admin_site
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter
from django.utils.html import format_html
from django.urls import reverse


# from lessons_bookings.models import Term


class TermFilter(admin.SimpleListFilter):
    title = 'Term Selection'
    parameter_name = 'term'
    default_value = 'CT'

    def lookups(self, request, model_admin):
        current_term = get_current_term()
        previous_term = get_previous_term()
        next_term = get_next_term()

        label_1 = f'Current Term: {current_term}'
        label_2 = f'Previous Term: {previous_term}'
        label_3 = f'Next Term: {next_term}'
        return [
            ('CT', label_1),
            ('PT', label_2),
            ('NT', label_3),
        ]

    def queryset(self, request, queryset):
        current_term = get_current_term()
        previous_term = get_previous_term()
        next_term = get_next_term()

        if self.value() == "CT":
            return queryset.filter(
                term=current_term
            )
        if self.value() == "PT":
            return queryset.filter(
                term=previous_term
            )
        if self.value() == "NT":
            return queryset.filter(
                term=next_term
            )


class CategoryFilter(admin.SimpleListFilter):
    title = 'Category'  # Human-readable title which will be displayed
    parameter_name = 'category'  # URL query parameter name

    def lookups(self, request, model_admin):
        # Assuming Category is related to Product
        categories = set(Product.objects.values_list('category__name', 'category__id'))
        return [(id, name) for name, id in categories]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(lesson__category__id=self.value())
        return queryset


class DayOfWeekFilter(admin.SimpleListFilter):
    title = 'Day of Week'
    parameter_name = 'day_of_week'

    def lookups(self, request, model_admin):
        return Product.DAY_CHOICES

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(lesson__day_of_week=self.value())
        return queryset


@admin.register(LessonEnrollment)
class LessonEnrollmentAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = EnrollmentResource
    list_display = ['swimling', 'term', 'lesson', 'order_link']
    list_display_links = ('swimling',)
    search_fields = ('swimling__first_name', 'swimling__last_name',)  # Adjust the fields based on your Swimling model
    list_filter = [TermFilter, CategoryFilter, DayOfWeekFilter, ('lesson', admin.RelatedOnlyFieldListFilter)]
    list_per_page = 20

    def order_link(self, obj):
        if obj.order:
            # Corrected URL pattern for the Order model's change page
            link = reverse("admin:lessons_orders_order_change", args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', link, obj.order)
        return '-'

    order_link.short_description = 'Order'


@admin.register(LessonAssignment)
class LessonAssignmentAdmin(admin.ModelAdmin):
    list_display = ('term', 'instructor', 'display_lessons')

    def display_lessons(self, obj):
        return ', '.join([lesson.name for lesson in obj.lessons.all()])

    display_lessons.short_description = 'Lessons Assigned'


class TermAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = TermResource
    list_display = ['id', 'start_date', 'end_date', 'rebooking_date', 'booking_date', 'assessment_date', 'changed_by']
    # Exclude the 'changed_by' field from the form fields
    exclude = ('changed_by',)

    def save_model(self, request, obj, form, change):
        if not change:  # If it's a new object being added
            obj.changed_by = request.user
        super().save_model(request, obj, form, change)


admin.site.register(Term, TermAdmin)

# Register to Custom Admin
lessons_admin_site.register(LessonEnrollment, LessonEnrollmentAdmin)
lessons_admin_site.register(Term, TermAdmin)
lessons_admin_site.register(LessonAssignment, LessonAssignmentAdmin)
