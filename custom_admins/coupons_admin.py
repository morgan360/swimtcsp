from django.contrib.admin import AdminSite
from django.contrib import admin
from coupons.models import Coupon, CouponRedemption
from coupons.utils import generate_coupon_code
from django.http import HttpResponse
import csv


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
