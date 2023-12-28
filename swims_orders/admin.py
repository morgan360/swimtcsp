import csv
import datetime
from django.contrib import admin
from .models import Order, OrderItem
from swims.models import PublicSwimProduct
import calendar
from django.utils import timezone
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponse
from custom_admins.swimsadmin import swims_admin_site
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter
from import_export.admin import ImportExportModelAdmin
from .resources import OrderResource, OrderItemResource
from django.utils import timezone
from datetime import timedelta

class SwimOrderItemInline(admin.TabularInline):
    model = OrderItem


def order_payment(obj):
    url = obj.get_stripe_url()
    if obj.stripe_id:
        html = f'<a href="{url}" target="_blank">{obj.stripe_id}</a>'
        return mark_safe(html)
    return ''


order_payment.short_description = 'Stripe payment'


def export_to_csv(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    content_disposition = f'attachment; filename={opts.verbose_name}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = content_disposition
    writer = csv.writer(response)
    fields = [field for field in opts.get_fields() if not \
        field.many_to_many and not field.one_to_many]
    # Write a first row with header information
    writer.writerow([field.verbose_name for field in fields])
    # Write data rows
    for obj in queryset:
        data_row = []
        for field in fields:
            value = getattr(obj, field.name)
            if isinstance(value, datetime.datetime):
                value = value.strftime('%d/%m/%Y')
            data_row.append(value)
        writer.writerow(data_row)
    return response


export_to_csv.short_description = 'Export to CSV'


@admin.register(Order)
class SwimOrderAdmin(ImportExportModelAdmin):
    resource_class = OrderResource
    list_display = ['id', 'get_product_name', 'short_booking_day', 'booking', 'paid', order_payment, 'user', 'created']
    list_filter = ['booking', 'paid', 'booking']
    inlines = [SwimOrderItemInline]
    actions = [export_to_csv]

    def get_product_name(self, obj):
        # Now directly accessing the product's name from the Order model
        return obj.product.name if obj.product else "No Product"

    get_product_name.short_description = 'Swim'

    def short_booking_day(self, obj):
        return calendar.day_abbr[obj.booking.weekday()]

    short_booking_day.short_description = '' \
                                          'Day'


# Register a model Second Time
class OrderProxy(Order):
    class Meta:
        proxy = True
        verbose_name_plural = "Today's Swim Orders"

    # You can customize the display name here
    def __str__(self):
        return f"Booked Today - {self.pk}"


@admin.register(OrderProxy)
class TodaySwimOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'paid', 'user', 'created']
    list_filter = ['booking', 'paid']
    ordering = ['-created']

    def get_queryset(self, request):
        # Get the current date in the timezone of the server
        current_date = timezone.now().date()
        # Filter orders with booking date equal to the current date
        queryset = super().get_queryset(request).filter(booking=current_date)
        return queryset

    def has_add_permission(self, request):
        return False  # Prevent adding new orders through this admin

    def has_delete_permission(self, request, obj=None):
        return False  # Prevent deleting orders through this admin

    def has_change_permission(self, request, obj=None):
        return False  # Prevent changing orders through this admin


swims_admin_site.register(Order, SwimOrderAdmin)


# Import order items
@admin.register(OrderItem)
class OrderItemAdmin(ImportExportModelAdmin):
    resource_class = OrderItemResource


swims_admin_site.register(OrderItem, OrderItemAdmin)


# see next seven days
class OrderNext7DaysProxy(Order):
    class Meta:
        proxy = True
        verbose_name = "Order in Next 7 Days"
        verbose_name_plural = "Orders in Next 7 Days"

    def __str__(self):
        return f"Swim Orders for Next 7 Days - {self.pk}"


@admin.register(OrderNext7DaysProxy)
class UpcomingSwimOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'paid', 'user', 'created']
    list_filter = ['booking', 'paid']
    ordering = ['booking']  # Orders are ordered by booking date

    def get_queryset(self, request):
        # Get the current date and the date 7 days from now
        current_date = timezone.now().date()
        end_date = current_date + timedelta(days=7)

        # Filter orders with booking date within the next 7 days
        queryset = super().get_queryset(request).filter(booking__range=[current_date, end_date])
        return queryset

    def has_add_permission(self, request):
        return False  # Prevent adding new orders through this admin

    def has_delete_permission(self, request, obj=None):
        return False  # Prevent deleting orders through this admin

    def has_change_permission(self, request, obj=None):
        return True  # Allow changing orders through this admin, if needed
