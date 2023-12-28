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
    stripe_id = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ['-created']
        indexes = [models.Index(fields=['booking'])]
        verbose_name = "Swim Order"
        verbose_name_plural = "Swim Orders"

    def __str__(self):
        return f'Order {self.id}'

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

    def get_stripe_url(self):
        if not self.stripe_id:
            return ''
        stripe_base_url = 'https://dashboard.stripe.com'
        path = '/test/' if '_test_' in settings.STRIPE_SECRET_KEY else '/'
        return f'{stripe_base_url}{path}payments/{self.stripe_id}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    variant = models.ForeignKey(PriceVariant, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Order Item {self.id} - {self.variant}"

    def get_cost(self):
        return self.variant.get_price() * self.quantity

    class Meta:
        verbose_name = "Swim Orderitem"
        verbose_name_plural = "Swim Orderitems"