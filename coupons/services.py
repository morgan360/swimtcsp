from decimal import Decimal
from django.utils import timezone
from .models import Coupon, CouponRedemption
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType

class CouponService:
    def __init__(self, coupon: Coupon):
        self.coupon = coupon

    def validate(self, user=None, amount=None):
        if not self.coupon.is_valid():
            raise ValidationError("Coupon is invalid or expired.")
        if self.coupon.assigned_to and user and self.coupon.assigned_to != user:
            raise ValidationError("This coupon is not assigned to you.")
        if amount is not None and self.coupon.balance_remaining <= Decimal('0.00'):
            raise ValidationError("Coupon has no remaining balance.")
        return True

    def apply(self, *, purchase_obj, amount: Decimal, user=None) -> Decimal:
        self.validate(user=user, amount=amount)
        if self.coupon.discount_type == 'fixed':
            discount = min(amount, self.coupon.balance_remaining)
        elif self.coupon.discount_type == 'percent':
            discount = amount * (self.coupon.discount_value / 100)
            discount = min(discount, self.coupon.balance_remaining)
        else:
            raise ValidationError("Unknown discount type.")

        # Deduct balance
        self.coupon.balance_remaining -= discount
        self.coupon.save()

        # Log redemption
        CouponRedemption.objects.create(
            coupon=self.coupon,
            redeemed_amount=discount,
            content_type=ContentType.objects.get_for_model(purchase_obj),
            object_id=purchase_obj.id
        )

        return discount
