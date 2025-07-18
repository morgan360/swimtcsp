# coupons/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('fixed', 'Fixed amount'),
        ('percent', 'Percentage'),
    ]

    code = models.CharField(max_length=20, unique=True, blank=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=6, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    active = models.BooleanField(default=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='user_specific_coupons',
        help_text='Optionally restrict this coupon to a specific user.'
    )
    balance_remaining = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_coupons'
    )

    def is_valid(self):
        now = timezone.now()
        return (
            self.active and
            self.valid_from <= now <= self.valid_to and
            self.balance_remaining > 0
        )

    def save(self, *args, **kwargs):
        if not self.pk and self.balance_remaining == 0:
            self.balance_remaining = self.discount_value
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code
