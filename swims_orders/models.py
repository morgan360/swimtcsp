from django.db import models
from swims.models import PublicSwimProduct
from django.conf import settings
from django.contrib.auth.models import User


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE,
                             related_name='swims_orders')
    # user = models.ForeignKey(User, on_delete=models.CASCADE,
    #                          related_name='swim_orders')
    # Product bought
    product_id = models.CharField(max_length=50, blank=True, null=True)
    # Date attending swim
    booking = models.DateField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)
    stripe_id = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ['booking']
        indexes = [
            models.Index(fields=['booking']),
        ]

    def __str__(self):
        return f'Order {self.id}'

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())

    def get_stripe_url(self):
        if not self.stripe_id:
            # no payment associated
            return ''
        if '_test_' in settings.STRIPE_SECRET_KEY:
            # Stripe path for test payments
            path = '/test/'
        else:
            # Stripe path for real payments
            path = '/'
        return f'https://dashboard.stripe.com{path}payments/{self.stripe_id}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order,
                              related_name='items',
                              on_delete=models.CASCADE)
    product = models.ForeignKey(PublicSwimProduct,
                                related_name='order_items',
                                on_delete=models.CASCADE)

    # Store the variant name as variants may change, same with price.
    variant = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=10,
                                decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity
