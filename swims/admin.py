from django.contrib import admin
from .models import PublicSwimCategory, PublicSwimProduct, PriceVariant
from .resources import PublicSwimCategoryResource, PublicSwimProductResource
from import_export.admin import ImportExportMixin
from django import forms
from custom_admins.swimsadmin import swims_admin_site
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter


# Prices Inline
class PriceVariantInline(admin.TabularInline):
    model = PriceVariant
    max_num = 4


@admin.register(PublicSwimCategory)
class CategoryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = PublicSwimCategoryResource
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


class PublicSwimProductAdminForm(forms.ModelForm):
    class Meta:
        model = PublicSwimProduct
        fields = '__all__'  # Include all fields in the form


class PublicSwimProductAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = PublicSwimProductResource
    form = PublicSwimProductAdminForm
    list_display = ['name', 'slug', 'available', 'created', 'updated']
    list_filter = ['available', 'created', 'updated']
    list_editable = ['available']
    inlines = [PriceVariantInline]

    fieldsets = (
        (None, {
            'fields': ('category', 'day_of_week', 'start_time', 'end_time', 'num_places', 'available')
        }),
        ('Additional Information', {
            'fields': ('description', 'image')
        }),
        ('Auto-Generated Fields', {
            'fields': ('name', 'slug'),
            'classes': ('collapse',),  # Hide the fieldset by default
        }),
    )


admin.site.register(PublicSwimProduct, PublicSwimProductAdmin)


@admin.register(PriceVariant)
class PriceVariantAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'variant', 'price']

    def product_name(self, obj):
        return obj.product.name

    product_name.short_description = 'Product'


swims_admin_site.register(PublicSwimProduct, PublicSwimProductAdmin)
swims_admin_site.register(PublicSwimCategory, CategoryAdmin)
swims_admin_site.register(PriceVariant, PriceVariantAdmin)