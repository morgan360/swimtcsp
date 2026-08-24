from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from lessons.models import Product
from django.conf import settings
from django.contrib.auth.models import User
from users.models import Swimling
from decimal import Decimal
from coupons.models import Coupon
# from lessons_bookings.models import Term


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)
    txId = models.CharField(max_length=250, blank=True)
    boipa_reconciled = models.BooleanField(default=False)
    payment_status = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    coupon = models.ForeignKey(



        Coupon,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='lesson_orders',  # 🔧 unique name
        help_text="Coupon used for this lesson order."
    )

    discount_amount = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        default=0,
        help_text="Total discount applied from the coupon."
    ),

    # CouponRedemption is the record of what was actually taken off this order,
    # written one row per coupon by CouponService.apply. It is the only reliable
    # source: `discount_amount` above never became a real database field (note
    # the trailing comma, which makes it a tuple) and migration 0009 dropped the
    # column, so assigning to it silently did nothing.
    #
    # Declared as a GenericRelation so callers listing orders can
    # prefetch_related('coupon_redemptions') instead of querying per row.
    coupon_redemptions = GenericRelation(
        'coupons.CouponRedemption',
        content_type_field='content_type',
        object_id_field='object_id',
    )

    @property
    def total_discount(self):
        """Total taken off this order across every coupon applied to it."""
        return sum(
            (r.redeemed_amount for r in self.coupon_redemptions.all()),
            Decimal('0.00'),
        )

    class Meta:
        verbose_name = "Lesson Order"
        verbose_name_plural = "Lesson Orders"
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
