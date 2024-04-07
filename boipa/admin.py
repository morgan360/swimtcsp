from django.contrib import admin
from .models import SwimOrderPaymentNotification


class SwimOrderPaymentNotificationAdmin(admin.ModelAdmin):
    list_display = (
        'txId',  'merchantTxId', 'amount', 'status')
    search_fields = ('txId', 'merchantTxId', 'amount', 'status')


admin.site.register(SwimOrderPaymentNotification, SwimOrderPaymentNotificationAdmin)

