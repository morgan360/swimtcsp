from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price', 'available', 'created', 'updated']
    list_filter = ['available', 'created', 'updated']
    list_editable = ['price', 'available']

    # Specify the choices for the day_of_week field
    # def day_of_week_display(self, obj):
    #     return dict(Product.DAY_CHOICES).get(obj.day_of_week)

    # day_of_week_display.short_description = 'Day of Week'
    #
    # list_display_links = ['name', 'slug']
    # list_display += ['day_of_week_display']  # Add to the existing list_display

    prepopulated_fields = {'slug': ('category', 'day_of_week', 'start_time',
                                    'end_time')}
