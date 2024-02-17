from django.contrib import admin
from custom_admins.lessonsadmin import lessons_admin_site
from .models import Program, Category, Product
from .resources import CategoryResource, ProductResource, ProgramResource
from import_export.admin import ImportExportMixin
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter


# class OccupancyAdmin(admin.ModelAdmin):
#     list_display = ['name', 'price', 'active', 'created', 'updated']
# admin.site.register(OccupancyAdmin)

# @admin.register(Product)
class ProductAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = ProductResource
    list_display = ['name', 'price', 'active', 'created', 'updated']
    list_filter = [('name', DropdownFilter), ('category', RelatedDropdownFilter), ('day_of_week', ChoiceDropdownFilter)]
    list_editable = ['price', 'active']

    fieldsets = (
        ('Times', {
            'classes': ('grp-collapse grp-open',),
            'fields': ('category', 'day_of_week', 'start_time', 'end_time', 'num_places', 'active')
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


admin.site.register(Product, ProductAdmin)


@admin.register(Program)
class ProgramAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = ProgramResource
    list_display = ['id', 'name']
    list_filter = [('name', DropdownFilter)]



@admin.register(Category)
class CategoryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = CategoryResource
    list_display = ['name', 'program', 'slug']


lessons_admin_site.register(Product, ProductAdmin)
lessons_admin_site.register(Category, CategoryAdmin)
lessons_admin_site.register(Program, ProgramAdmin)
