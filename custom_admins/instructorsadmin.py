from django.contrib.admin import AdminSite
from django.contrib import admin
from instructors.models import InstructorAssignment, InstructorProfile

# ✅ Step 1: Create the custom admin site
class InstructorsAdminSite(AdminSite):
    site_header = "Instructor Admin"
    site_title = "Instructor Admin Portal"
    index_title = "Instructor Management"

# ✅ Step 2: Define the site *before* using it
instructors_admin_site = InstructorsAdminSite(name='instructorsadmin')

# ✅ Step 3: Register models to this custom site (not the default one!)
@admin.register(InstructorAssignment, site=instructors_admin_site)
class InstructorAssignmentAdmin(admin.ModelAdmin):
    list_display = ('lesson', 'term', 'instructor')
    list_filter = [
        ('term', admin.RelatedOnlyFieldListFilter),        # Custom filter UI for terms
        ('instructor', admin.RelatedOnlyFieldListFilter),  # ✅ Add instructor filter
    ]
    ordering = ['-term__start_date']  # ✅ Reverse order by term start date
    search_fields = ('lesson__name', 'instructor__first_name', 'instructor__last_name')
    # autocomplete_fields = ['lesson', 'term', 'instructor']

@admin.register(InstructorProfile, site=instructors_admin_site)
class InstructorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'qualification_level')
    search_fields = ('user__first_name', 'user__last_name', 'user__email')
