from django.contrib import admin
from .models import Group, Program, Category, Product
from .resources import CategoryResource, ProductResource
from import_export.admin import ImportExportMixin


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
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

    fieldsets = (
        (None, {
            'fields': ('category', 'day_of_week', 'start_time', 'end_time', 'num_places', 'active')
        }),
        ('Additional Information', {
            'fields': ('description', 'image')
        }),
        ('Auto-Generated Fields', {
            'fields': ('name', 'slug'),
            'classes': ('collapse',),  # Hide the fieldset by default
        }),
    )


admin.site.register(Product, ProductAdmin)
