from django.contrib import admin
from django.utils import timezone
from .models import WaitingList
from lessons.models import Product
from django.contrib import admin
from django.utils import timezone
from .models import WaitingList

@admin.register(WaitingList)
class WaitingListAdmin(admin.ModelAdmin):
    list_display = ('swimling', 'product', 'get_guardian', 'is_notified', 'assigned_lesson', 'completed' ,'created_at')
    list_filter = ('is_notified', 'created_at')
    search_fields = ('swimling__first_name', 'swimling__last_name', 'product__name', 'swimling__guardian__username')
    actions = ['assign_lesson_and_notify']

    def get_guardian(self, obj):
        return obj.swimling.guardian
    get_guardian.short_description = "Guardian"
    get_guardian.admin_order_field = 'swimling__guardian'
