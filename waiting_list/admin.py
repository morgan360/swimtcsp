from django.contrib import admin
from django.utils import timezone
from .models import WaitingList
from lessons.models import Product
from .utils import send_waiting_list_notification


class WaitingListAdmin(admin.ModelAdmin):
    list_display = ('swimling', 'product', 'user', 'is_notified', 'assigned_lesson', 'created_at')
    list_filter = ('is_notified', 'created_at')
    search_fields = ('swimling__first_name', 'swimling__last_name', 'product__name', 'user__username')
    actions = ['assign_lesson_and_notify']

    def assign_lesson_and_notify(self, request, queryset):
        for entry in queryset:
            if entry.assigned_lesson:
                send_waiting_list_notification(
                    entry.user.email,
                    entry.swimling.first_name,
                    entry.assigned_lesson.name
                )
                entry.is_notified = True
                entry.notification_date = timezone.now()
                entry.save()
        self.message_user(request, "Selected swimlings have been assigned to a lesson and notified.")

    assign_lesson_and_notify.short_description = "Assign lesson and notify customer"

    def save_model(self, request, obj, form, change):
        # Detect if is_notified changed from False to True
        should_notify = False
        if obj.pk:
            old_obj = WaitingList.objects.get(pk=obj.pk)
            if not old_obj.is_notified and obj.is_notified:
                should_notify = True

        super().save_model(request, obj, form, change)

        if should_notify and obj.assigned_lesson:
            send_waiting_list_notification(
                obj.user.email,
                obj.swimling.first_name,
                obj.assigned_lesson.name
            )
            if not obj.notification_date:
                obj.notification_date = timezone.now()
                obj.save()
