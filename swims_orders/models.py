from django.db import models
from swims.models import PublicSwimProduct, PriceVariant
from django.conf import settings


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE,
                             related_name='swims_orders')
    # Product bought - now a direct reference to PublicSwimProduct
    product = models.ForeignKey(PublicSwimProduct, on_delete=models.CASCADE, blank=True, null=True)
    # Date attending swim
    booking = models.DateField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)
    txId = models.CharField(max_length=250, blank=True)
    payment_status = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ['-created']
        indexes = [models.Index(fields=['booking'])]
        verbose_name = "Swim Order"
        verbose_name_plural = "Swim Orders"

    def __str__(self):
        return f'Order {self.id}'

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

    def get_boipa_backoffice_url(self):
        """
        Returns the URL for the BOIPA Back-Office. If direct linking to a transaction detail
        page becomes available, this method can be updated accordingly.
        """
        return "https://backofficeui-apiuat.test.boipapaymentgateway.com/"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey(PriceVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Order Item {self.id} - {self.variant}"

    def get_cost(self):
        return self.variant.get_price() * self.quantity

    def get_unit_price(self):
        return self.variant.get_price()

    class Meta:
        verbose_name = "Swim Orderitem"
        verbose_name_plural = "Swim Orderitems"
