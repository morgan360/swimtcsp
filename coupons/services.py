from decimal import Decimal
from django.utils import timezone
from .models import Coupon, CouponRedemption
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType


MAX_COUPONS_PER_ORDER = 2


def compute_cart_totals(*, user, subtotal: Decimal, codes, context='lessons'):
    """
    Dry-run computation of multi-coupon totals for a cart. No DB writes.

    Returns a dict with subtotal, total_discount, final_price, applied list of
    {'code', 'coupon', 'discount'}, and errors list of {'code', 'message'}.
    Invalid codes are dropped and reported in errors so the caller can decide
    whether to surface them.

    Each coupon's discount is capped at the remaining cart balance so two
    fixed-amount coupons on a cart smaller than their combined face value
    never push the total below €0.
    """
    applied = []
    errors = []
    remaining = subtotal
    for code in codes:
        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            errors.append({'code': code, 'message': 'Invalid coupon code'})
            continue
        service = CouponService(coupon)
        try:
            service.validate(user=user, amount=subtotal, context=context)
        except ValidationError as e:
            errors.append({'code': code, 'message': str(e)})
            continue
        if coupon.discount_type == 'fixed':
            cap = coupon.discount_value if coupon.multi_use else coupon.balance_remaining
            discount = min(cap, remaining)
        elif coupon.discount_type == 'percent':
            discount = min(subtotal * (coupon.discount_value / Decimal('100')), remaining)
        else:
            errors.append({'code': code, 'message': 'Unknown discount type'})
            continue
        applied.append({'code': code, 'coupon': coupon, 'discount': discount})
        remaining -= discount

    total_discount = subtotal - remaining
    return {
        'subtotal': subtotal,
        'total_discount': total_discount,
        'final_price': remaining,
        'applied': applied,
        'errors': errors,
    }


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

        # Only check balance for single-use coupons (multi-use coupons keep their balance)
        if not self.coupon.multi_use and amount is not None and self.coupon.balance_remaining <= Decimal('0.00'):
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
                context_names = {
                    'lessons': 'lesson bookings',
                    'schools': 'school bookings',
                    'swims': 'public swim bookings',
                    'admin': 'admin use'
                }
                raise ValidationError(
                    f"This coupon can only be used for {context_names.get(self.coupon.usage_context, 'specific purposes')}."
                )

        # Check product restrictions
        if product and not self.coupon.can_be_used_for_product(product):
            raise ValidationError("This coupon cannot be used for this product.")

        return True

    def apply(self, *, purchase_obj, amount: Decimal, user=None, product=None, context='any', discount_cap: Decimal = None) -> Decimal:
        """
        Apply this coupon, writing a CouponRedemption row.

        `amount` is validated against (e.g. minimum_order_value) and used as the
        basis for percentage discounts. `discount_cap`, if provided, limits the
        actual discount taken — used when stacking coupons so each redemption
        only takes what remains of the cart.

        Takes the coupon's balance and usage immediately. Checkouts that still
        have to be paid for use reserve() instead.
        """
        self.validate(user=user, amount=amount, product=product, context=context)
        discount = self._discount(amount, discount_cap)
        self._take(discount, user)
        self._record(purchase_obj, discount, confirmed=True)
        return discount

    def reserve(self, *, purchase_obj, amount: Decimal, user=None, product=None, context='any', discount_cap: Decimal = None) -> Decimal:
        """
        Price this coupon into an order that is about to go to payment.

        Same checks and discount as apply(), but the coupon's balance and usage
        are left alone: the redemption is written as pending and only taken by
        confirm_pending_redemptions() once the order is paid. A parent who
        abandons or fails payment keeps their coupon.
        """
        self.validate(user=user, amount=amount, product=product, context=context)
        discount = self._discount(amount, discount_cap)
        self._record(purchase_obj, discount, confirmed=False)
        return discount

    def _discount(self, amount, discount_cap=None):
        cap = amount if discount_cap is None else discount_cap
        if self.coupon.discount_type == 'fixed':
            if self.coupon.multi_use:
                # Multi-use coupons: apply discount_value each time without depleting balance
                return min(cap, self.coupon.discount_value)
            # Single-use coupons: deplete from remaining balance
            return min(cap, self.coupon.balance_remaining)
        if self.coupon.discount_type == 'percent':
            return min(amount * (self.coupon.discount_value / Decimal('100')), cap)
        raise ValidationError("Unknown discount type.")

    def _take(self, discount, user=None):
        # For single-use coupons, deduct balance
        # For multi-use coupons, don't touch balance (it stays at discount_value)
        if not self.coupon.multi_use:
            self.coupon.balance_remaining = max(self.coupon.balance_remaining - discount, Decimal('0.00'))

        # Increment usage counter for all coupons
        self.coupon.times_used += 1
        self.coupon.save()

        # Track which user used this coupon (only for single-use to prevent reuse)
        if user and not self.coupon.multi_use:
            self.coupon.used_by_users.add(user)

    def _record(self, purchase_obj, discount, *, confirmed):
        CouponRedemption.objects.create(
            coupon=self.coupon,
            redeemed_amount=discount,
            content_type=ContentType.objects.get_for_model(purchase_obj),
            object_id=purchase_obj.id,
            confirmed=confirmed,
        )


def confirm_pending_redemptions(purchase_obj):
    """
    Take the coupons reserved on a now-paid order. Safe to call repeatedly:
    BOIPA's return page and webhook can both report the same payment, and only
    redemptions still pending are processed.
    """
    from django.db import transaction

    pending = CouponRedemption.objects.filter(
        content_type=ContentType.objects.get_for_model(purchase_obj),
        object_id=purchase_obj.id,
        confirmed=False,
    )
    if not pending.exists():
        return
    with transaction.atomic():
        for redemption in pending.select_for_update():
            coupon = Coupon.objects.select_for_update().get(pk=redemption.coupon_id)
            CouponService(coupon)._take(redemption.redeemed_amount, getattr(purchase_obj, 'user', None))
            redemption.confirmed = True
            redemption.save(update_fields=['confirmed'])
