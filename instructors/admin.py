from django.contrib import admin
from .models import InstructorAssignment, InstructorProfile

# @admin.register(InstructorAssignment)
# class InstructorAssignmentAdmin(admin.ModelAdmin):
#     list_display = ('lesson', 'term_label', 'instructor')
#     list_filter = ('term',)
#     search_fields = ('lesson__name', 'instructor__first_name', 'instructor__last_name')
#     autocomplete_fields = ['lesson', 'term', 'instructor']

#     def term_label(self, obj):
#         return obj.term.label
#     term_label.short_description = "Term"

# @admin.register(InstructorProfile)
# class InstructorProfileAdmin(admin.ModelAdmin):
#     list_display = ('user', 'qualification_level')
#     search_fields = ('user__first_name', 'user__last_name', 'user__email')
