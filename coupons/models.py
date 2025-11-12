# coupons/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

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

    # Multi-use feature
    multi_use = models.BooleanField(
        default=False,
        help_text='If enabled, this coupon can be used multiple times (balance permitting). If disabled, coupon is single-use only.'
    )
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Maximum number of times this coupon can be used. Leave blank for unlimited uses (balance permitting).'
    )
    times_used = models.PositiveIntegerField(
        default=0,
        help_text='Number of times this coupon has been used.'
    )

    # Product limitation
    limited_to_products = models.ManyToManyField(
        'lessons.Product',
        blank=True,
        related_name='limited_coupons',
        help_text='If selected, this coupon can only be used for these specific products. Leave blank to allow all products.'
    )

    # Category and Program restrictions
    limited_to_categories = models.ManyToManyField(
        'lessons.Category',
        blank=True,
        related_name='limited_coupons',
        help_text='If selected, this coupon can only be used for products in these categories. Leave blank to allow all categories.'
    )
    limited_to_programs = models.ManyToManyField(
        'lessons.Program',
        blank=True,
        related_name='limited_coupons',
        help_text='If selected, this coupon can only be used for products in these programs. Leave blank to allow all programs.'
    )

    # Minimum purchase amount
    minimum_order_value = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Minimum order value required to use this coupon. Leave blank for no minimum.'
    )

    # Usage context restriction
    USAGE_CONTEXT_CHOICES = [
        ('any', 'Any (Lessons, Schools, Swims, Admin)'),
        ('lessons', 'Lessons Only'),
        ('schools', 'Schools Only'),
        ('swims', 'Public Swims Only'),
        ('admin', 'Admin Use Only'),
    ]
    usage_context = models.CharField(
        max_length=10,
        choices=USAGE_CONTEXT_CHOICES,
        default='any',
        help_text='Restrict where this coupon can be used.'
    )

    # User usage tracking
    used_by_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='used_coupons',
        help_text='Tracks which users have used this coupon.'
    )

    # New field
    note = models.CharField(max_length=255, blank=True, null=True, help_text="Optional note")
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
        is_time_valid = self.active and self.valid_from <= now <= self.valid_to

        # Only check balance for single-use coupons
        # Multi-use coupons keep their balance and don't deplete it
        if self.multi_use:
            has_balance = True  # Multi-use coupons always have balance
        else:
            has_balance = self.balance_remaining > 0

        # Check multi-use limits
        if self.multi_use and self.max_uses is not None:
            has_uses_remaining = self.times_used < self.max_uses
        else:
            has_uses_remaining = True

        return is_time_valid and has_balance and has_uses_remaining

    def can_be_used_for_product(self, product):
        """Check if coupon can be used for a specific product"""
        # Check direct product restrictions
        if self.limited_to_products.exists():
            if not self.limited_to_products.filter(id=product.id).exists():
                return False

        # Check category restrictions
        if self.limited_to_categories.exists():
            if not product.category or not self.limited_to_categories.filter(id=product.category.id).exists():
                return False

        # Check program restrictions
        if self.limited_to_programs.exists():
            if not product.category or not product.category.program or \
               not self.limited_to_programs.filter(id=product.category.program.id).exists():
                return False

        return True

    def can_be_used_by_user(self, user):
        """Check if a user can use this coupon"""
        if not self.multi_use:
            # Single-use coupon: check if user has already used it
            return not self.used_by_users.filter(id=user.id).exists()
        return True  # Multi-use coupons can be reused by same user

    def save(self, *args, **kwargs):
        if not self.pk and self.balance_remaining == 0:
            self.balance_remaining = self.discount_value
        super().save(*args, **kwargs)

    def __str__(self):
        return self.code

# Tracks all product redemptions

class CouponRedemption(models.Model):
    coupon = models.ForeignKey('Coupon', on_delete=models.CASCADE, related_name='redemptions')
    redeemed_amount = models.DecimalField(max_digits=6, decimal_places=2)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    # GFK to any purchase model: SwimOrder, LessonBooking, etc.
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    redeemed_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"{self.coupon.code} redeemed {self.redeemed_amount} on {self.redeemed_object}"
