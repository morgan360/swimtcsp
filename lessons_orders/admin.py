from django.contrib import admin
from .models import Order, OrderItem
from django.utils.safestring import mark_safe
from custom_admins.lessonsadmin import lessons_admin_site
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product', 'term']


@admin.action(description="Refund selected orders via BOIPA")
def refund_orders(modeladmin, request, queryset):
    from boipa.utils import refund_boipa_transaction

    for order in queryset:
        if order.paid and order.txId:
            result = refund_boipa_transaction(order.txId, order.amount, order=order)
            if result["success"]:
                order.payment_status = "refunded"
                order.save()


class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "paid", "payment_status", "amount", "created")
    list_filter = ['paid', 'created', 'updated']
    actions = [refund_orders]
    inlines = [OrderItemInline]


# Register to Custom Admin Site Only
lessons_admin_site.register(Order, OrderAdmin)
