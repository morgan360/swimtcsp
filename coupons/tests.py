from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from coupons.models import Coupon, CouponRedemption
from coupons.services import CouponService, compute_cart_totals

User = get_user_model()


def make_coupon(code, value="20.00", discount_type="fixed", **kwargs):
    now = timezone.now()
    opts = dict(
        code=code,
        discount_type=discount_type,
        discount_value=Decimal(value),
        balance_remaining=Decimal(value),
        valid_from=now - timedelta(days=1),
        valid_to=now + timedelta(days=30),
    )
    opts.update(kwargs)
    return Coupon.objects.create(**opts)


class ComputeCartTotalsTests(TestCase):
    """
    The dry run behind the cart page. It must agree with what checkout goes on
    to charge, so the arithmetic is pinned here rather than only end to end.
    """

    def setUp(self):
        self.user = User.objects.create_user(email="totals@example.com", password="pw12345!")

    def totals(self, codes, subtotal="100.00"):
        return compute_cart_totals(
            user=self.user, subtotal=Decimal(subtotal), codes=codes, context="lessons"
        )

    def test_no_codes_leaves_the_subtotal_alone(self):
        result = self.totals([])
        self.assertEqual(result["total_discount"], Decimal("0.00"))
        self.assertEqual(result["final_price"], Decimal("100.00"))
        self.assertEqual(result["applied"], [])

    def test_two_fixed_coupons_stack(self):
        make_coupon("STACK-A", "20.00")
        make_coupon("STACK-B", "15.00")

        result = self.totals(["STACK-A", "STACK-B"])

        self.assertEqual([a["code"] for a in result["applied"]], ["STACK-A", "STACK-B"])
        self.assertEqual([a["discount"] for a in result["applied"]],
                         [Decimal("20.00"), Decimal("15.00")])
        self.assertEqual(result["total_discount"], Decimal("35.00"))
        self.assertEqual(result["final_price"], Decimal("65.00"))

    def test_combined_value_over_the_cart_is_capped_at_zero(self):
        """Two coupons worth more than the cart must not produce a negative total."""
        make_coupon("BIG-A", "80.00")
        make_coupon("BIG-B", "50.00")

        result = self.totals(["BIG-A", "BIG-B"], subtotal="100.00")

        self.assertEqual(result["final_price"], Decimal("0.00"))
        self.assertEqual(result["total_discount"], Decimal("100.00"))
        # The second coupon only takes what was left, not its full face value.
        self.assertEqual(result["applied"][0]["discount"], Decimal("80.00"))
        self.assertEqual(result["applied"][1]["discount"], Decimal("20.00"))

    def test_percent_is_taken_off_the_subtotal_not_the_running_balance(self):
        make_coupon("HALF", "50.00", discount_type="percent")
        make_coupon("TENNER", "10.00")

        result = self.totals(["HALF", "TENNER"])

        self.assertEqual(result["applied"][0]["discount"], Decimal("50.00"))
        self.assertEqual(result["applied"][1]["discount"], Decimal("10.00"))
        self.assertEqual(result["final_price"], Decimal("40.00"))

    def test_a_bad_code_is_reported_and_the_good_one_still_applies(self):
        make_coupon("GOOD", "20.00")

        result = self.totals(["GOOD", "NO-SUCH-CODE"])

        self.assertEqual([a["code"] for a in result["applied"]], ["GOOD"])
        self.assertEqual([e["code"] for e in result["errors"]], ["NO-SUCH-CODE"])
        self.assertEqual(result["final_price"], Decimal("80.00"))

    def test_wrong_context_coupon_is_rejected_not_silently_discounted(self):
        make_coupon("SCHOOLS-ONLY", "20.00", usage_context="schools")

        result = self.totals(["SCHOOLS-ONLY"])

        self.assertEqual(result["applied"], [])
        self.assertEqual([e["code"] for e in result["errors"]], ["SCHOOLS-ONLY"])
        self.assertEqual(result["final_price"], Decimal("100.00"))

    def test_dry_run_writes_nothing(self):
        make_coupon("UNTOUCHED", "20.00")

        self.totals(["UNTOUCHED"])

        coupon = Coupon.objects.get(code="UNTOUCHED")
        self.assertEqual(coupon.times_used, 0)
        self.assertEqual(coupon.balance_remaining, Decimal("20.00"))
        self.assertEqual(CouponRedemption.objects.count(), 0)


class StackedApplyTests(TestCase):
    """CouponService.apply with a discount_cap — the write side of the same sum."""

    def setUp(self):
        self.user = User.objects.create_user(email="apply@example.com", password="pw12345!")
        # Any saved model will do as the redemption's target.
        self.purchase = User.objects.create_user(email="target@example.com", password="pw12345!")

    def test_cap_limits_what_the_second_coupon_takes(self):
        first = make_coupon("CAP-A", "80.00")
        second = make_coupon("CAP-B", "50.00")
        subtotal = Decimal("100.00")

        taken_first = CouponService(first).apply(
            purchase_obj=self.purchase, amount=subtotal, user=self.user,
            context="lessons", discount_cap=subtotal,
        )
        taken_second = CouponService(second).apply(
            purchase_obj=self.purchase, amount=subtotal, user=self.user,
            context="lessons", discount_cap=subtotal - taken_first,
        )

        self.assertEqual(taken_first, Decimal("80.00"))
        self.assertEqual(taken_second, Decimal("20.00"))
        self.assertEqual(subtotal - taken_first - taken_second, Decimal("0.00"))

        # Only the amount actually taken comes off the balance, so the unused
        # €30 stays on the second coupon for another order.
        second.refresh_from_db()
        self.assertEqual(second.balance_remaining, Decimal("30.00"))

    def test_each_application_records_its_own_redemption(self):
        first = make_coupon("REC-A", "20.00")
        second = make_coupon("REC-B", "15.00")
        subtotal = Decimal("100.00")

        CouponService(first).apply(
            purchase_obj=self.purchase, amount=subtotal, user=self.user,
            context="lessons", discount_cap=subtotal,
        )
        CouponService(second).apply(
            purchase_obj=self.purchase, amount=subtotal, user=self.user,
            context="lessons", discount_cap=subtotal - Decimal("20.00"),
        )

        redemptions = CouponRedemption.objects.order_by("id")
        self.assertEqual(redemptions.count(), 2)
        self.assertEqual(
            [r.redeemed_amount for r in redemptions],
            [Decimal("20.00"), Decimal("15.00")],
        )
