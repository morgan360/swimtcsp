from django.contrib import admin
from .models import Category, Product
from .resources import ProductResource
from import_export.admin import ImportExportMixin

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = ProductResource
    list_display = ['name', 'slug', 'price', 'available', 'created', 'updated']
    list_filter = ['available', 'created', 'updated']
    list_editable = ['price', 'available']

    prepopulated_fields = {'slug': ('category', 'day_of_week', 'start_time',
                                    'end_time')}
