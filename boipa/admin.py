from django.contrib import admin
from .models import PaymentNotification


class PaymentNotificationAdmin(admin.ModelAdmin):
    list_display = (
        'txId',  'merchantTxId', 'amount', 'status')
    search_fields = ('txId', 'merchantTxId', 'amount', 'status')


admin.site.register(PaymentNotification, PaymentNotificationAdmin)

