from django.db import models

class PaymentNotification(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='notifications')
    txId = models.CharField(max_length=50)  # The unique identifier for the transaction in the BOIPA Gateway
    merchantTxId = models.CharField(max_length=50)  # The merchant’s reference for the transaction provided in the
    country = models.CharField(max_length=2, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, null=True, blank=True)
    action = models.CharField(max_length=10, null=True, blank=True)
    auth_code = models.CharField(max_length=10, null=True, blank=True)  # Extracted from paymentSolutionDetails
    acquirer = models.CharField(max_length=100, null=True, blank=True)
    acquirerAmount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    merchantId = models.CharField(max_length=50, null=True, blank=True)
    brandId = models.CharField(max_length=50, null=True, blank=True)
    customerId = models.CharField(max_length=50, null=True)
    acquirerCurrency = models.CharField(max_length=3, null=True, blank=True)
    paymentSolutionId = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.txId