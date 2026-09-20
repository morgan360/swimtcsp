from django.contrib import admin
from .models import SwimOrderPaymentNotification, LessonOrderPaymentNotification, SchoolOrderPaymentNotification
from custom_admins.base import TCSPModelAdmin


class SwimOrderPaymentNotificationAdmin(TCSPModelAdmin):
    """Read-only: these are the gateway's records, not ours to edit."""

    list_display = ('txId', 'merchantTxId', 'amount', 'status', 'auth_code')
    search_fields = ('txId', 'merchantTxId', 'status')
    list_filter = ('status',)

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(SwimOrderPaymentNotification, SwimOrderPaymentNotificationAdmin)

class LessonOrderPaymentNotificationAdmin(TCSPModelAdmin):
    """Read-only: these are the gateway's records, not ours to edit."""

    list_display = ('txId', 'merchantTxId', 'amount', 'status', 'auth_code')
    search_fields = ('txId', 'merchantTxId', 'status')
    list_filter = ('status',)

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(LessonOrderPaymentNotification, LessonOrderPaymentNotificationAdmin)

class SchoolOrderPaymentNotificationAdmin(TCSPModelAdmin):
    """Read-only: these are the gateway's records, not ours to edit."""

    list_display = ('txId', 'merchantTxId', 'amount', 'status', 'auth_code')
    search_fields = ('txId', 'merchantTxId', 'status')
    list_filter = ('status',)

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(SchoolOrderPaymentNotification, SchoolOrderPaymentNotificationAdmin)



