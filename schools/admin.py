from django.contrib import admin
from import_export.admin import ImportExportMixin
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter

from custom_admins.schoolsadmin import schools_admin_site

from schools.models import ScoLessons, ScoCategory, ScoProgram, ScoSchool
from schools_orders.models import Order
from schools_bookings.models import ScoTerm, ScoEnrollment

from .resources import CategoryResource, ProductResource, ProgramResource, SchoolResource


# ✅ Helper to avoid AlreadyRegistered error
from django.contrib.admin.sites import AlreadyRegistered

def safe_register(site, model, admin_class=None):
    try:
        site.register(model, admin_class)
    except AlreadyRegistered:
        pass


class ScoLessonsAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = ProductResource
    list_display = ['name', 'price', 'active', 'school', 'created', 'updated']
    list_filter = [
        ('name', DropdownFilter),
        ('category', RelatedDropdownFilter),
        ('day_of_week', ChoiceDropdownFilter)
    ]
    list_editable = ['price', 'active']
    related_lookup_fields = {'fk': ['area']}
    fieldsets = (
        ('Times', {
            'classes': ('grp-collapse grp-open',),
            'fields': ('category', 'day_of_week', 'start_time', 'end_time', 'num_places', 'active', 'school')
        }),
        ('Additional Information', {
            'classes': ('grp-collapse grp-closed',),
            'fields': ('description', 'image')
        }),
        ('Auto-Generated Fields', {
            'classes': ('grp-collapse grp-closed',),
            'fields': ('name', 'slug'),
        }),
    )


class ScoProgramAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = ProgramResource
    list_display = ['id', 'name']
    list_filter = [('name', DropdownFilter)]


class ScoCategoryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = CategoryResource
    list_display = ['name', 'program', 'slug']


class ScoSchoolAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = SchoolResource

    def get_list_display(self, request):
        return [field.name for field in ScoSchool._meta.fields]


# ✅ Safe registration of models to custom admin site
safe_register(schools_admin_site, ScoLessons, ScoLessonsAdmin)
safe_register(schools_admin_site, ScoCategory, ScoCategoryAdmin)
safe_register(schools_admin_site, ScoProgram, ScoProgramAdmin)
safe_register(schools_admin_site, ScoSchool, ScoSchoolAdmin)
safe_register(schools_admin_site, Order)
safe_register(schools_admin_site, ScoTerm)
safe_register(schools_admin_site, ScoEnrollment)
