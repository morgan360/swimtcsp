from django.contrib import admin
from .models import SwimOrderPaymentNotification, LessonOrderPaymentNotification, SchoolOrderPaymentNotification
from custom_admins.base import TCSPModelAdmin


class SwimOrderPaymentNotificationAdmin(TCSPModelAdmin):
    list_display = (
        'txId',  'merchantTxId', 'amount', 'status')
    search_fields = ('txId', 'merchantTxId', 'amount', 'status')


admin.site.register(SwimOrderPaymentNotification, SwimOrderPaymentNotificationAdmin)

class LessonOrderPaymentNotificationAdmin(TCSPModelAdmin):
    list_display = (
        'txId',  'merchantTxId', 'amount', 'status')
    search_fields = ('txId', 'merchantTxId', 'amount', 'status')

admin.site.register(LessonOrderPaymentNotification, LessonOrderPaymentNotificationAdmin)

class SchoolOrderPaymentNotificationAdmin(TCSPModelAdmin):
    list_display = (
        'txId',  'merchantTxId', 'amount', 'status')
    search_fields = ('txId', 'merchantTxId', 'amount', 'status')

admin.site.register(SchoolOrderPaymentNotification, SchoolOrderPaymentNotificationAdmin)



