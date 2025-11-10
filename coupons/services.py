from decimal import Decimal
from django.utils import timezone
from .models import Coupon, CouponRedemption
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType

class CouponService:
    def __init__(self, coupon: Coupon):
        self.coupon = coupon

    def validate(self, user=None, amount=None, product=None, context='any'):
        """
        Validate coupon usage

        Args:
            user: User attempting to use the coupon
            amount: Order amount (before discount)
            product: Product being purchased (optional)
            context: Usage context ('lessons', 'schools', 'admin', or 'any')
        """
        if not self.coupon.is_valid():
            raise ValidationError("Coupon is invalid or expired.")

        if self.coupon.assigned_to and user and self.coupon.assigned_to != user:
            raise ValidationError("This coupon is not assigned to you.")

        if amount is not None and self.coupon.balance_remaining <= Decimal('0.00'):
            raise ValidationError("Coupon has no remaining balance.")

        # Check if single-use coupon has already been used globally
        if not self.coupon.multi_use and self.coupon.times_used >= 1:
            raise ValidationError("This coupon has already been used.")

        # Check if user has already used this coupon (for single-use coupons)
        if user and not self.coupon.can_be_used_by_user(user):
            raise ValidationError("You have already used this coupon.")

        # Check minimum order value
        if self.coupon.minimum_order_value and amount is not None:
            if amount < self.coupon.minimum_order_value:
                raise ValidationError(
                    f"Minimum order value of €{self.coupon.minimum_order_value} required to use this coupon."
                )

        # Check usage context
        if self.coupon.usage_context != 'any' and context != 'any':
            if self.coupon.usage_context != context:
                context_names = {'lessons': 'lesson bookings', 'schools': 'school bookings', 'admin': 'admin use'}
                raise ValidationError(
                    f"This coupon can only be used for {context_names.get(self.coupon.usage_context, 'specific purposes')}."
                )

        # Check product restrictions
        if product and not self.coupon.can_be_used_for_product(product):
            raise ValidationError("This coupon cannot be used for this product.")

        return True

    def apply(self, *, purchase_obj, amount: Decimal, user=None, product=None, context='any') -> Decimal:
        self.validate(user=user, amount=amount, product=product, context=context)
        if self.coupon.discount_type == 'fixed':
            discount = min(amount, self.coupon.balance_remaining)
        elif self.coupon.discount_type == 'percent':
            discount = amount * (self.coupon.discount_value / 100)
            discount = min(discount, self.coupon.balance_remaining)
        else:
            raise ValidationError("Unknown discount type.")

        # Deduct balance and increment usage counter
        self.coupon.balance_remaining -= discount
        self.coupon.times_used += 1
        self.coupon.save()

        # Track which user used this coupon
        if user:
            self.coupon.used_by_users.add(user)

        # Log redemption
        CouponRedemption.objects.create(
            coupon=self.coupon,
            redeemed_amount=discount,
            content_type=ContentType.objects.get_for_model(purchase_obj),
            object_id=purchase_obj.id
        )

        return discount
