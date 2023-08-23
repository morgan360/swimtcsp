from django.contrib import admin
from import_export.admin import ImportExportMixin
from .models import Term, LessonAssignment, LessonEnrollment
from .resources import TermResource  # Make sure to import the resource class
from django.contrib.auth import get_user_model


@admin.register(LessonEnrollment)
class LessonEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'swimling', 'lesson']
    list_display_links = ('id',)
    list_editable = ['lesson']
    search_fields = ('swimling',)
    list_filter = ('term', 'lesson')


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
