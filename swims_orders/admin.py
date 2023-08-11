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


class SwimOrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']


def order_payment(obj):
    url = obj.get_stripe_url()
    if obj.stripe_id:
        html = f'<a href="{url}" target="_blank">{obj.stripe_id}</a>'
        return mark_safe(html)
    return ''


order_payment.short_description = 'Stripe payment'


@admin.register(Order)
class SwimOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_product_names', 'short_booking_day',
                    'booking', 'paid', order_payment, 'user', 'created', ]
    list_filter = ['booking', 'paid', 'booking']
    inlines = [SwimOrderItemInline]
    actions = [export_to_csv]

    def get_product_names(self, obj):
        # Get a list of product names for the current order
        product_ids = OrderItem.objects.filter(order=obj).values_list(
            'product_id', flat=True)
        products = PublicSwimProduct.objects.filter(id__in=product_ids)
        return ", ".join([product.name for product in products])

    get_product_names.short_description = 'Session'

    def short_booking_day(self, obj):
        return calendar.day_abbr[obj.booking.weekday()]

    short_booking_day.short_description = '' \
                                          'Day'


# Register a model Second Time
class OrderProxy(Order):
    class Meta:
        proxy = True
        verbose_name_plural = "Today's Orders"

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
