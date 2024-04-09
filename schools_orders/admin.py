from django.contrib import admin
from .models import Order, OrderItem
from django.utils.safestring import mark_safe
from custom_admins.lessonsadmin import lessons_admin_site
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product', 'term']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'paid', 'user',
                    'created', 'updated']
    list_filter = ['paid', 'created', 'updated']
    inlines = [OrderItemInline]


# Register to Custom Admin
lessons_admin_site.register(Order, OrderAdmin)
