from django.contrib import admin
from .models import WaitingList
from lessons.models import Product  # Import the Product model
from .utils import send_waiting_list_notification  # Ensure this function is defined to send notifications


class WaitingListAdmin(admin.ModelAdmin):
    list_display = ('swimling', 'product', 'user', 'is_notified', 'assigned_lesson', 'created_at')
    list_filter = ('is_notified', 'created_at')
    search_fields = ('swimling__first_name', 'swimling__last_name', 'product__name', 'user__username')
    actions = ['assign_lesson_and_notify']

    def assign_lesson_and_notify(self, request, queryset):
        for entry in queryset:
            if entry.assigned_lesson:
                # Notify the customer
                send_waiting_list_notification(
                    entry.user.email,
                    entry.swimling.first_name,  # assuming swimling has a first_name attribute
                    entry.assigned_lesson.name
                )
                # Update the entry
                entry.is_notified = True
                entry.notification_date = timezone.now()
                entry.save()
        self.message_user(request, "Selected swimlings have been assigned to a lesson and notified.")

    assign_lesson_and_notify.short_description = "Assign lesson and notify customer"


admin.site.register(WaitingList, WaitingListAdmin)
