from django.contrib import admin
from .models import Group, Program, Category, Product
from .resources import GroupResource, CategoryResource, ProductResource
from import_export.admin import ImportExportMixin


@admin.register(Program)
class ProgramAdmin( admin.ModelAdmin):

    list_display = ['name']


@admin.register(Group)
class GroupAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = GroupResource
    list_display = ['name']


@admin.register(Category)
class CategoryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = CategoryResource
    list_display = ['name', 'program', 'slug']


# @admin.register(Product)
class ProductAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = ProductResource
    list_display = ['name', 'slug', 'price', 'active', 'created', 'updated']
    list_filter = ['active', 'created', 'updated']
    list_editable = ['price', 'active']
    related_lookup_fields = {
        'fk': ['group'],
    }
    fieldsets = (
        ('Times', {
            'classes': ('grp-collapse grp-open',),
            'fields': ('category', 'day_of_week', 'start_time', 'end_time', 'num_places', 'active', 'group')
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
