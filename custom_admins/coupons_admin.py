from django.contrib.admin import AdminSite
from django.contrib import admin
from coupons.models import Coupon
from coupons.utils import generate_coupon_code

# ✅ Define the custom admin site
class CouponsAdminSite(AdminSite):
    site_header = "Coupons Admin"
    site_title = "Coupons Admin Portal"
    index_title = "Manage Coupons"

coupons_admin_site = CouponsAdminSite(name='couponsadmin')

@admin.register(Coupon, site=coupons_admin_site)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'discount_type',
        'discount_value',
        'balance_remaining',
        'valid_from',
        'valid_to',
        'active',
        'assigned_to',  # ✅ Optional: show who it’s for
        'is_valid_now',
    )
    list_filter = ('active', 'valid_from', 'valid_to', 'discount_type')
    search_fields = ('code', 'assigned_to__email')

    readonly_fields = ('code', 'created_at', 'updated_at', 'created_by')

    fields = (
        'code',
        'discount_type',
        'discount_value',
        'balance_remaining',
        'valid_from',
        'valid_to',
        'active',
        'assigned_to',
        'created_at',
        'updated_at',
        'created_by',
    )

    def is_valid_now(self, obj):
        return obj.is_valid()
    is_valid_now.boolean = True
    is_valid_now.short_description = "Valid Now"

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.code:
            obj.code = generate_coupon_code()
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
