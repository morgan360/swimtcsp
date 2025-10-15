from django.db import models
from schools.models import ScoLessons, ScoSchool
from django.conf import settings
from django.contrib.auth.models import User
from users.models import Swimling
from decimal import Decimal
from coupons.models import Coupon

# from lessons_bookings.models import Term


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='schools_orders')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)
    txId = models.CharField(max_length=250, blank=True)
    boipa_reconciled = models.BooleanField(default=False)
    payment_status = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    school = models.ForeignKey(ScoSchool, on_delete=models.CASCADE, related_name='orders', null=True, blank=True)

    coupon = models.ForeignKey(
        Coupon,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='school_orders',
        help_text="Coupon used for this school order."
    )

    discount_amount = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        blank=True,
        help_text="Total discount applied via coupon."
    )

    class Meta:
        verbose_name = "School Order"
        verbose_name_plural = "School Orders"
        ordering = ['-created']
        indexes = [
            models.Index(fields=['-created']),
        ]

    def __str__(self):
        return f'Order {self.id}'

    def get_total_cost(self):
        return sum(item.get_cost() for item in self.items.all())


class OrderItem(models.Model):
    term = models.ForeignKey('schools_bookings.ScoTerm', on_delete=models.SET_NULL, null=True)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(ScoLessons,
                                related_name='sco_order_items',
                                on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10,
                                decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    swimling = models.ForeignKey(Swimling,
                                 related_name='sco_swimling',
                                 on_delete=models.CASCADE)

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity
