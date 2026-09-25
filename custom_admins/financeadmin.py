from django.contrib import admin, messages
from django.shortcuts import render
from django.contrib.admin import ModelAdmin, TabularInline, register

from custom_admins.base import MANAGER_AND_FULL_TIMER, TCSPAdminSite, TCSPModelAdmin
from django.db.models import Sum
from django.utils.timezone import localtime
from django.http import HttpResponse
import csv

# Import all Order models
from swims_orders.models import Order as SwimOrder, OrderItem as SwimOrderItem
from lessons_orders.models import Order as LessonOrder, OrderItem as LessonOrderItem
from schools_orders.models import Order as SchoolOrder, OrderItem as SchoolOrderItem
from boipa.models import Refund

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
class FinanceAdminSite(TCSPAdminSite):
    site_header = "💶 TCSP Finance"
    site_title = "Finance"
    index_title = "Orders, coupons, reconciliation and revenue"
    index_template = "admin/financeadmin/index.html"
    panel_icon = "💶"
    panel_path = "/finance/"
    required_groups = MANAGER_AND_FULL_TIMER

    def get_urls(self):
        from django.urls import path
        from functools import partial
        from finances import views as fv

        custom_urls = [
            path('revenue/', self.admin_view(
                partial(fv.revenue_report, template_name='admin/financeadmin/revenue_report.html')
            ), name='revenue_report'),
            path('revenue/table/', self.admin_view(fv.revenue_report_table), name='revenue_report_table'),
            path('revenue/chart-data/', self.admin_view(fv.revenue_chart_data), name='revenue_chart_data'),
            path('revenue/daily-orders/', self.admin_view(fv.revenue_daily_orders), name='revenue_daily_orders'),
            path('revenue/export/csv/', self.admin_view(fv.revenue_export_csv), name='revenue_export_csv'),
            path('reconciliation/', self.admin_view(
                partial(fv.reconciliation_dashboard, template_name='admin/financeadmin/reconciliation.html')
            ), name='reconciliation'),
            path('reconciliation/table/', self.admin_view(fv.reconciliation_table), name='reconciliation_table'),
            path('reconciliation/verify/<str:order_type>/<int:order_id>/',
                 self.admin_view(fv.reconciliation_verify), name='reconciliation_verify'),
            path('reconciliation/details/<str:order_type>/<int:order_id>/',
                 self.admin_view(fv.reconciliation_details), name='reconciliation_details'),
            path('reconciliation/export/csv/', self.admin_view(fv.reconciliation_export_csv), name='reconciliation_export_csv'),
        ]
        return custom_urls + super().get_urls()

    def each_context(self, request):
        from django.urls import reverse
        context = super().each_context(request)
        context['revenue_report_url'] = reverse('finance:revenue_report')
        context['reconciliation_url'] = reverse('finance:reconciliation')
        return context


finance_admin_site = FinanceAdminSite(name="finance")


# ---------------------------
# Base Admin for all Orders
# ---------------------------
class BaseOrderAdmin(TCSPModelAdmin):
    # Walked by user_email, which list_display cannot reveal.
    list_select_related_extra = ("user",)

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
    actions = ["export_to_csv", "verify_with_boipa", "refund_orders"]

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
    @admin.action(description="Refund selected orders via BOIPA")
    def refund_orders(self, request, queryset):
        """Refund through BOIPA, behind a confirmation page.

        This previously lived on the lessons panel, reachable by any staff
        member, and fired the moment you picked it from the dropdown — no
        confirmation, no error handling, no report of what happened.
        """
        from boipa.utils import refund_boipa_transaction

        refundable, skipped = [], []
        for order in queryset:
            if order.paid and getattr(order, "txId", None) and order.payment_status != "refunded":
                refundable.append(order)
            else:
                skipped.append(order)

        if request.POST.get("confirmed") != "yes":
            return render(request, "admin/financeadmin/refund_confirmation.html", {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "queryset": queryset,
                "refundable": refundable,
                "skipped": skipped,
            })

        done, failed = 0, 0
        for order in refundable:
            try:
                result = refund_boipa_transaction(order.txId, order.amount, order=order)
            except Exception as exc:
                failed += 1
                messages.error(request, f"Order #{order.id}: refund raised {exc}")
                continue
            if result.get("success"):
                order.payment_status = "refunded"
                order.save(update_fields=["payment_status"])
                done += 1
            else:
                failed += 1
                messages.error(request, f"Order #{order.id}: BOIPA refused the refund "
                                        f"({result.get('message', 'no reason given')})")

        if done:
            messages.success(request, f"Refunded {done} order(s).")
        if skipped:
            messages.warning(request, f"Skipped {len(skipped)} order(s) — unpaid, "
                                      "already refunded, or with no transaction id.")
        if not done and not failed:
            messages.info(request, "Nothing was refunded.")

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
# Order line items
# ---------------------------
# Opening an order here used to show only the order-level fields (guardian,
# amount, paid), with no way to see which swimmer or which class the money was
# for without cross-referencing another admin. These inlines put the line items
# on the order page. Finance is a reconciliation view, so they are read-only --
# amounts must not be editable from a reporting screen.
class BaseOrderItemInline(TabularInline):
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class LessonOrderItemInline(BaseOrderItemInline):
    model = LessonOrderItem
    fields = ("swimling", "product", "term", "price", "quantity")
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("swimling", "product", "term")


class SchoolOrderItemInline(BaseOrderItemInline):
    model = SchoolOrderItem
    fields = ("swimling", "product", "term", "price", "quantity")
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("swimling", "product", "term")


class SwimOrderItemInline(BaseOrderItemInline):
    # Public swims are ticket purchases, not per-child enrolments, so there is
    # no swimling to show -- the variant is the meaningful detail.
    model = SwimOrderItem
    fields = ("variant", "quantity")
    readonly_fields = fields

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("variant")


# ---------------------------
# Register models
# ---------------------------
@register(SwimOrder, site=finance_admin_site)
class SwimOrderAdmin(BaseOrderAdmin):
    inlines = [SwimOrderItemInline]


@register(LessonOrder, site=finance_admin_site)
class LessonOrderAdmin(BaseOrderAdmin):
    inlines = [LessonOrderItemInline]


@register(SchoolOrder, site=finance_admin_site)
class SchoolOrderAdmin(BaseOrderAdmin):
    inlines = [SchoolOrderItemInline]


# Refunds sit with the orders they reverse. They were on Operations under a
# "Boipa" heading, which staff reasonably read as the reconciliation tools.
@register(Refund, site=finance_admin_site)
class RefundAdmin(TCSPModelAdmin):
    """Read-only: a refund record is written by the gateway callback."""

    list_display = ['id', 'order', 'tx_id', 'amount', 'created']
    search_fields = ['tx_id', 'order__id']
    list_filter = ['created']

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
