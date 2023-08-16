from django.contrib import admin
from import_export.admin import ImportExportMixin
from .models import Term
from .resources import TermResource
from .models import LessonAssignment, LessonEnrollment


@admin.register(LessonEnrollment)
class YourModelNameAdmin(admin.ModelAdmin):
    list_display = ['id','swimling', 'lesson',]
    list_display_links = ('id',)
    list_editable = ['lesson', ]
    search_fields = ('swimling',)
    list_filter = ('term', 'lesson')

# Assign Lessons to instructors
@admin.register(LessonAssignment)
class LessonAssignmentAdmin(admin.ModelAdmin):
    list_display = ('term', 'instructor', 'display_lessons')

    def display_lessons(self, obj):
        return ', '.join([lesson.name for lesson in obj.lessons.all()])

    display_lessons.short_description = 'Lessons Assigned'


class TermAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = TermResource
    list_display = ['term_id', 'start', 'end', 'rebooking',
                    'booking', 'assessments']


admin.site.register(Term, TermAdmin)
