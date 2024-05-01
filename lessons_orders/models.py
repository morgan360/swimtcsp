from django.db import models
from lessons.models import Product
from django.conf import settings
from django.contrib.auth.models import User
from users.models import Swimling
from decimal import Decimal

# from lessons_bookings.models import Term


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)
    txId = models.CharField(max_length=250, blank=True)
    payment_status = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['-created']),
        ]

    def __str__(self):
        return f'Order {self.id}'

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())


class OrderItem(models.Model):
    term = models.ForeignKey('lessons_bookings.Term', on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey(Order,
                              related_name='items',
                              on_delete=models.CASCADE)
    product = models.ForeignKey(Product,
                                related_name='order_items',
                                on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10,
                                decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    swimling = models.ForeignKey(Swimling,
                                 related_name='swimling',
                                 on_delete=models.CASCADE)

    class Meta:
        unique_together = ('order', 'product', 'swimling')

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity
