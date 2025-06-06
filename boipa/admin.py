from django.contrib import admin
from .models import SwimOrderPaymentNotification, LessonOrderPaymentNotification, SchoolOrderPaymentNotification


class SwimOrderPaymentNotificationAdmin(admin.ModelAdmin):
    list_display = (
        'txId',  'merchantTxId', 'amount', 'status')
    search_fields = ('txId', 'merchantTxId', 'amount', 'status')


admin.site.register(SwimOrderPaymentNotification, SwimOrderPaymentNotificationAdmin)

class LessonOrderPaymentNotificationAdmin(admin.ModelAdmin):
    list_display = (
        'txId',  'merchantTxId', 'amount', 'status')
    search_fields = ('txId', 'merchantTxId', 'amount', 'status')

admin.site.register(LessonOrderPaymentNotification, LessonOrderPaymentNotificationAdmin)

class SchoolOrderPaymentNotificationAdmin(admin.ModelAdmin):
    list_display = (
        'txId',  'merchantTxId', 'amount', 'status')
    search_fields = ('txId', 'merchantTxId', 'amount', 'status')

admin.site.register(SchoolOrderPaymentNotification, SchoolOrderPaymentNotificationAdmin)



