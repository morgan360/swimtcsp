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
    list_display = ['name', 'available', 'created', 'updated']
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
    list_filter = [('name' , DropdownFilter),('category', RelatedDropdownFilter),('day_of_week',  ChoiceDropdownFilter),('available')]

admin.site.register(PublicSwimProduct, PublicSwimProductAdmin)


@admin.register(PriceVariant)
class PriceVariantAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'variant', 'price']
    # Every swim carries five variants, so this list is five times the length of
    # the swims list and the day and category a price belongs to are only
    # readable inside the product name. Filter on the product's own fields.
    list_filter = [
        ('product__day_of_week', ChoiceDropdownFilter),
        ('product__category', RelatedDropdownFilter),
    ]
    # product_name reads through to the product on every row.
    list_select_related = ('product', 'product__category')

    def product_name(self, obj):
        return obj.product.name

    product_name.short_description = 'Product'
    product_name.admin_order_field = 'product__name'


swims_admin_site.register(PublicSwimProduct, PublicSwimProductAdmin)
swims_admin_site.register(PublicSwimCategory, CategoryAdmin)
swims_admin_site.register(PriceVariant, PriceVariantAdmin)