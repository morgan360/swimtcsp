from django.contrib import admin
from custom_admins.lessonsadmin import lessons_admin_site
from .models import ScoArea, ScoLessons, ScoCategory, ScoProgram, ScoSchool
from .resources import AreaResource, CategoryResource, ProductResource, ProgramResource, SchoolResource
from import_export.admin import ImportExportMixin
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter


class ProductAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = ProductResource
    list_display = ['name', 'price', 'active','school', 'created', 'updated']
    list_filter = [('name', DropdownFilter), ('category', RelatedDropdownFilter), ('day_of_week', ChoiceDropdownFilter)]
    list_editable = ['price', 'active']
    related_lookup_fields = {
        'fk': ['area'],
    }
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


admin.site.register(ScoLessons, ProductAdmin)


@admin.register(ScoProgram)
class ProgramAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = ProgramResource
    list_display = ['id', 'name']
    list_filter = [('name', DropdownFilter)]


@admin.register(ScoArea)
class AreaAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = AreaResource
    list_display = ['id', 'name']


@admin.register(ScoCategory)
class CategoryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = CategoryResource
    list_display = ['name', 'program', 'slug']


@admin.register(ScoSchool)
class ScoSchoolAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = SchoolResource

    def get_list_display(self, request):
        return [field.name for field in ScoSchool._meta.fields]


lessons_admin_site.register(ScoLessons, ProductAdmin)
lessons_admin_site.register(ScoArea, AreaAdmin)
lessons_admin_site.register(ScoCategory, CategoryAdmin)
lessons_admin_site.register(ScoProgram, ProgramAdmin)
