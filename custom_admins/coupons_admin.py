from django.contrib.admin import AdminSite
from django.contrib import admin
from coupons.models import Coupon, CouponRedemption
from coupons.utils import generate_coupon_code
from django.http import HttpResponse
import csv
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter
from django.contrib.auth import get_user_model
from lessons.models import Product, Category, Program

User = get_user_model()

# ✅ Define the custom admin site *first*
class CouponsAdminSite(AdminSite):
    site_header = "Coupons Admin"
    site_title = "Coupons Admin Portal"
    index_title = "Manage Coupons"

coupons_admin_site = CouponsAdminSite(name='couponsadmin')


# ✅ Minimal User admin for coupons site autocomplete
class UserAutocompleteAdmin(admin.ModelAdmin):
    search_fields = ('email', 'first_name', 'last_name')
    list_display = ('email', 'first_name', 'last_name')  # optional

# ✅ Minimal Product admin for filter_horizontal widget
class ProductListAdmin(admin.ModelAdmin):
    search_fields = ('name', 'category__name')
    list_display = ('name', 'category')
    list_filter = ('category',)

# ✅ Minimal Category admin
class CategoryListAdmin(admin.ModelAdmin):
    search_fields = ('name', 'program__name')
    list_display = ('name', 'program')
    list_filter = ('program',)

# ✅ Minimal Program admin
class ProgramListAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    list_display = ('name',)

try:
    coupons_admin_site.register(User, UserAutocompleteAdmin)
    coupons_admin_site.register(Product, ProductListAdmin)
    coupons_admin_site.register(Category, CategoryListAdmin)
    coupons_admin_site.register(Program, ProgramListAdmin)
except admin.sites.AlreadyRegistered:
    pass


@admin.register(Coupon, site=coupons_admin_site)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'active',
        'is_valid_now',
        'discount_type',
        'amount_display',
        'balance_display',
        'multi_use',
        'usage_display',
        'note',
        'created_by',
        'assigned_to',
    )
    list_editable = ('note', 'active',)
    list_filter = (
        'active',
        'multi_use',
        ('assigned_to', RelatedDropdownFilter),
    )
    autocomplete_fields = ['assigned_to']
    search_fields = ('code', 'assigned_to__email', 'note')
    readonly_fields = ('code', 'created_at', 'updated_at', 'created_by', 'times_used', 'users_who_used')
    filter_horizontal = ('limited_to_products', 'limited_to_categories', 'limited_to_programs', 'used_by_users')

    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'discount_type', 'discount_value', 'balance_remaining', 'minimum_order_value')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to', 'active')
        }),
        ('Usage Context', {
            'fields': ('usage_context',),
            'description': 'Restrict where this coupon can be used (lessons, schools, or admin only).'
        }),
        ('Multi-Use Settings', {
            'fields': ('multi_use', 'max_uses', 'times_used'),
            'description': 'Control whether this coupon can be used multiple times.'
        }),
        ('Restrictions', {
            'fields': ('limited_to_products', 'limited_to_categories', 'limited_to_programs'),
            'description': 'Optionally restrict this coupon by product, category, or program. More specific restrictions (products) take precedence. Leave all blank to allow everything.'
        }),
        ('Assignment & Notes', {
            'fields': ('assigned_to', 'note')
        }),
        ('Tracking', {
            'fields': ('created_at', 'updated_at', 'created_by', 'users_who_used'),
            'classes': ('collapse',)
        }),
    )

    def amount_display(self, obj):
        return obj.discount_value
    amount_display.short_description = "Amount"

    def balance_display(self, obj):
        return obj.balance_remaining
    balance_display.short_description = "Balance"

    def is_valid_now(self, obj):
        return obj.is_valid()
    is_valid_now.boolean = True
    is_valid_now.short_description = "Valid"

    def usage_display(self, obj):
        if not obj.multi_use:
            return "Single-use"
        if obj.max_uses:
            return f"{obj.times_used}/{obj.max_uses}"
        return f"{obj.times_used}/∞"
    usage_display.short_description = "Usage"

    def users_who_used(self, obj):
        """Display list of users who have used this coupon"""
        users = obj.used_by_users.all()[:10]  # Limit to first 10
        if not users:
            return "None yet"
        user_list = ", ".join([u.email for u in users])
        if obj.used_by_users.count() > 10:
            user_list += f" ... and {obj.used_by_users.count() - 10} more"
        return user_list
    users_who_used.short_description = "Used By (Users)"

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.code:
            obj.code = generate_coupon_code()
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CouponRedemption, site=coupons_admin_site)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = (
        'coupon',
        'redeemed_amount',
        'redeemed_at',
        'redeemed_object_display',
    )
    readonly_fields = ('coupon', 'redeemed_amount', 'redeemed_at', 'redeemed_object')
    search_fields = ('coupon__code',)
    list_filter = ('redeemed_at', 'coupon__code')
    actions = ['export_as_csv']

    def redeemed_object_display(self, obj):
        return str(obj.redeemed_object)
    redeemed_object_display.short_description = "Used On"

    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="coupon_redemptions.csv"'

        writer = csv.writer(response)
        writer.writerow(['Coupon Code', 'Redeemed Amount', 'Redeemed At', 'Used On (Type/ID)'])

        for redemption in queryset:
            used_on = f"{redemption.content_type.model} #{redemption.object_id}"
            writer.writerow([
                redemption.coupon.code,
                redemption.redeemed_amount,
                redemption.redeemed_at.strftime('%Y-%m-%d %H:%M:%S'),
                used_on
            ])

        return response

    export_as_csv.short_description = "Export selected redemptions as CSV"
