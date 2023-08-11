from django.contrib import admin
from .models import PublicSwimCategory, PublicSwimProduct, PriceVariant


# Prices Inline
class PriceVariantInline(admin.TabularInline):
    model = PriceVariant
    max_num = 4


@admin.register(PublicSwimCategory)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(PublicSwimProduct)
class PublicSwimProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug',
                    'available', 'created', 'updated']
    list_filter = ['available', 'created', 'updated']
    list_editable = ['available']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [PriceVariantInline]


@admin.register(PriceVariant)
class PriceVariantAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'variant', 'price']

    def product_name(self, obj):
        return obj.product.name

    product_name.short_description = 'Product'
