from django.contrib import messages
from django.contrib.admin import AdminSite, ModelAdmin, register
from django.db.models import Sum
from django.utils.timezone import localtime
from django.http import HttpResponse
import csv

# Import all Order models
from swims_orders.models import Order as SwimOrder
from lessons_orders.models import Order as LessonOrder
from schools_orders.models import Order as SchoolOrder

# Date range filter
from rangefilter.filters import DateRangeFilter

from django.utils import timezone
from django.contrib.admin import SimpleListFilter
from datetime import timedelta

class TodayFilter(SimpleListFilter):
    title = "Date"
    parameter_name = "created_today"

    def lookups(self, request, model_admin):
        return [("today", "Today")]

    def queryset(self, request, queryset):
        if self.value() == "today":
            now = timezone.now()
            start = timezone.make_aware(
                timezone.datetime.combine(now.date(), timezone.datetime.min.time())
            )
            end = start + timedelta(days=1)
            return queryset.filter(created__gte=start, created__lt=end)
        return queryset
# ---------------------------
# BOIPA verification helper
# ---------------------------
from boipa.utils import verify_boipa_transaction


# ---------------------------
# Custom Finance Admin Site
# ---------------------------
class FinanceAdminSite(AdminSite):
    site_header = "Finance Admin"
    site_title = "Finance Admin Portal"
    index_title = "Finance Overview"
    index_template = "admin/financeadmin/index.html"

    def each_context(self, request):
        context = super().each_context(request)
        context['revenue_report_url'] = '/finances/revenue/'
        context['reconciliation_url'] = '/finances/reconciliation/'
        return context


finance_admin_site = FinanceAdminSite(name="financeadmin")


# ---------------------------
# Base Admin for all Orders
# ---------------------------
class BaseOrderAdmin(ModelAdmin):
    list_display = (
        "order_number",
        'txId',
        "created_fmt",
        "user_email",
        "product_display",
        "amount_fmt",
        "paid",
        "boipa_reconciled_display",   # ✅ new column
    )
    list_display_links = ("order_number", "created_fmt")
    list_filter = (
        "paid",
        "boipa_reconciled",
        TodayFilter,
        ("created", DateRangeFilter),
    )
    search_fields = ("id", "user__email", "txId")
    ordering = ("-created",)
    actions = ["export_to_csv", "verify_with_boipa"]

    # ✅ Default: show only paid orders
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if "paid__exact" not in request.GET:
            qs = qs.filter(paid=True)
        return qs

    # ✅ Default: preselect "Paid = Yes" in sidebar filter
    def changelist_view(self, request, extra_context=None):
        if "paid__exact" not in request.GET:
            q = request.GET.copy()
            q["paid__exact"] = "1"
            request.GET = q
            request.META["QUERY_STRING"] = request.GET.urlencode()
        response = super().changelist_view(request, extra_context)
        try:
            cl = response.context_data["cl"]
            qs = cl.queryset
            totals = qs.aggregate(total_amount=Sum("amount"))
            response.context_data["summary_total"] = totals["total_amount"] or 0
        except Exception:
            pass
        return response

    # Display helpers
    def order_number(self, obj):
        return obj.id
    order_number.short_description = "Order #"

    def created_fmt(self, obj):
        return localtime(obj.created).strftime("%Y-%m-%d %H:%M")
    created_fmt.short_description = "Date"

    def user_email(self, obj):
        return getattr(obj.user, "email", "—")
    user_email.short_description = "Guardian"

    def product_display(self, obj):
        """Display the main product or lesson name gracefully."""
        if hasattr(obj, "product"):
            return getattr(obj.product, "name", str(obj.product))
        if hasattr(obj, "items"):
            first_item = obj.items.first()
            if first_item and hasattr(first_item, "product"):
                return getattr(first_item.product, "name", str(first_item.product))
            if obj.items.exists():
                return f"{obj.items.count()} item(s)"
        return "—"
    product_display.short_description = "Product(s)"

    def amount_fmt(self, obj):
        return f"€{obj.amount:.2f}"
    amount_fmt.short_description = "Amount"

    # ✅ New display for reconciliation status
    def boipa_reconciled_display(self, obj):
        return "✅" if getattr(obj, "boipa_reconciled", False) else "—"
    boipa_reconciled_display.short_description = "Reconciled"
    boipa_reconciled_display.admin_order_field = "boipa_reconciled"

    # ✅ Admin action: Verify with BOIPA
    def verify_with_boipa(self, request, queryset):
        success, fail = 0, 0
        for order in queryset:
            tx_id = getattr(order, "txId", None)
            if tx_id:
                confirmed = verify_boipa_transaction(tx_id)
                order.boipa_reconciled = confirmed
                order.save(update_fields=["boipa_reconciled"])
                if confirmed:
                    success += 1
                else:
                    fail += 1
            else:
                fail += 1
        self.message_user(
            request,
            f"BOIPA reconciliation complete: {success} matched, {fail} failed.",
            level=messages.INFO,
        )
    verify_with_boipa.short_description = "Verify selected with BOIPA"

    # CSV Export Action
    def export_to_csv(self, request, queryset):
        meta = self.model._meta
        filename = f"{meta.app_label}_{meta.model_name}.csv"
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow([
            "Order #", "Date", "Guardian", "Product(s)",
            "Amount (€)", "Paid", "Reconciled"
        ])
        for o in queryset:
            writer.writerow([
                o.id,
                localtime(o.created).strftime("%Y-%m-%d %H:%M"),
                getattr(o.user, "email", "—"),
                self.product_display(o),
                f"{o.amount:.2f}",
                "Yes" if o.paid else "No",
                "Yes" if getattr(o, "boipa_reconciled", False) else "No",
            ])
        return response
    export_to_csv.short_description = "Export selected to CSV"


# ---------------------------
# Register models
# ---------------------------
@register(SwimOrder, site=finance_admin_site)
class SwimOrderAdmin(BaseOrderAdmin):
    pass


@register(LessonOrder, site=finance_admin_site)
class LessonOrderAdmin(BaseOrderAdmin):
    pass


@register(SchoolOrder, site=finance_admin_site)
class SchoolOrderAdmin(BaseOrderAdmin):
    pass
