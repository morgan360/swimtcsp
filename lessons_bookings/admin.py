from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from import_export.admin import ImportExportMixin
from .models import Term, LessonAssignment, LessonEnrollment
from .resources import EnrollementResource, TermResource
from django.contrib.auth import get_user_model
import django_filters
from utils.terms_utils import get_current_term, get_previous_term, get_next_term
from custom_admins.lessonsadmin import lessons_admin_site
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter

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


@admin.register(LessonEnrollment)
class LessonEnrollmentAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = EnrollementResource
    list_display = ['swimling', 'term', 'lesson']
    list_display_links = ('swimling',)
    # list_editable = ['lesson']
    # search_fields = ('swimling',)
    list_filter = [TermFilter, ('lesson', admin.RelatedOnlyFieldListFilter)]
    list_per_page = 20


#     def get_queryset(self, request):
#         queryset = super().get_queryset(request)
#         specific_term = Term.objects.get(id=48)  # Replace with your desired term
#         queryset = queryset.filter(term=specific_term).select_related('swimling', 'lesson').prefetch_related(
#             'order__id')
#         return queryset

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