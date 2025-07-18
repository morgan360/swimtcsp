from .models import Coupon
from django.utils import timezone

# Ensures uniqueness and valid format
from django.utils.crypto import get_random_string

def generate_coupon_code(prefix="TCSP", length=5):
    while True:
        suffix = get_random_string(length=length, allowed_chars='ABCDEFGHJKLMNPQRSTUVWXYZ23456789')
        code = f"{prefix}-{suffix}"
        if not Coupon.objects.filter(code=code).exists():
            return code

def apply_coupon(code, total):
    try:
        coupon = Coupon.objects.get(code__iexact=code)
        if not coupon.is_valid():
            return total, "Coupon is invalid, expired, or fully used"

        if coupon.discount_type == 'fixed':
            discount = min(coupon.discount_value, coupon.balance_remaining, total)
        elif coupon.discount_type == 'percent':
            discount = total * coupon.discount_value / 100
            discount = min(discount, coupon.balance_remaining)
        else:
            discount = 0

        new_total = max(total - discount, 0)
        coupon.balance_remaining -= discount
        coupon.save()
        return new_total, None

    except Coupon.DoesNotExist:
        return total, "Coupon code not found"
