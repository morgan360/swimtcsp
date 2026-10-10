from datetime import time

from django.test import TestCase
from django.urls import reverse

from swims.models import PriceVariant, PublicSwimCategory, PublicSwimProduct
from users.models import User


class PriceVariantFilterTests(TestCase):
    """The price list runs five rows per swim, so it filters by day and category."""

    @classmethod
    def setUpTestData(cls):
        cls.lane = PublicSwimCategory.objects.create(name="Lane Swim", slug="lane-swim")
        cls.family = PublicSwimCategory.objects.create(name="Family Swim", slug="family-swim")

        cls.mon_lane = cls._make_swim(cls.lane, 0, time(7, 0))
        cls.tue_lane = cls._make_swim(cls.lane, 1, time(7, 0))
        cls.mon_family = cls._make_swim(cls.family, 0, time(15, 0))

        cls.staff = User.objects.create_superuser(
            email="admin@tcsp.ie", password="pw", first_name="Admin"
        )

    @classmethod
    def _make_swim(cls, category, day_of_week, start_time):
        swim = PublicSwimProduct.objects.create(
            category=category,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=time(start_time.hour + 1, start_time.minute),
            num_places=20,
            available=True,
        )
        PriceVariant.objects.create(product=swim, variant="Adult", price=8)
        PriceVariant.objects.create(product=swim, variant="Child", price=5)
        return swim

    def setUp(self):
        self.client.force_login(self.staff)

    def _changelist(self, **params):
        url = reverse('operations:swims_pricevariant_changelist')
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, 200)
        return response

    def _swims_listed(self, response):
        return {variant.product for variant in response.context['cl'].queryset}

    def test_the_unfiltered_list_holds_every_price(self):
        self.assertEqual(self._changelist().context['cl'].queryset.count(), 6)

    def test_filtering_by_day_keeps_only_that_days_prices(self):
        response = self._changelist(product__day_of_week__exact='0')
        self.assertEqual(self._swims_listed(response), {self.mon_lane, self.mon_family})

    def test_filtering_by_category_keeps_only_that_categorys_prices(self):
        response = self._changelist(product__category__id__exact=str(self.lane.id))
        self.assertEqual(self._swims_listed(response), {self.mon_lane, self.tue_lane})

    def test_day_and_category_narrow_together(self):
        response = self._changelist(
            product__day_of_week__exact='0',
            product__category__id__exact=str(self.lane.id),
        )
        self.assertEqual(self._swims_listed(response), {self.mon_lane})


class SwimCouponCheckoutTests(TestCase):
    """Swim coupons go through the same checks as lessons and are only spent once paid."""

    @classmethod
    def setUpTestData(cls):
        from datetime import timedelta
        from decimal import Decimal
        from django.utils import timezone
        from coupons.models import Coupon

        category = PublicSwimCategory.objects.create(name="Lane Swim", slug="lane-swim")
        cls.swim = PublicSwimProduct.objects.create(
            category=category, day_of_week=0, start_time=time(7, 0), end_time=time(8, 0),
            num_places=20, available=True,
        )
        cls.adult = PriceVariant.objects.create(product=cls.swim, variant="Adult", price=Decimal("8.00"))
        cls.parent = User.objects.create_user(email="swimmer@example.com", password="pw", first_name="S")
        cls.other = User.objects.create_user(email="other@example.com", password="pw", first_name="O")
        now = timezone.now()

        def coupon(code, value, **kw):
            return Coupon.objects.create(
                code=code, discount_type="fixed", discount_value=Decimal(value),
                balance_remaining=Decimal(value), valid_from=now - timedelta(days=1),
                valid_to=now + timedelta(days=30), **kw,
            )
        cls.five = coupon("SWIM5", "5.00")
        cls.ten = coupon("SWIM10", "10.00")
        cls.not_yours = coupon("NOTYOURS", "5.00", assigned_to=cls.other)

    def setUp(self):
        self.client.force_login(self.parent)
        self.url = reverse("swims:product_detail", args=[self.swim.id, self.swim.slug])

    def book(self, code):
        return self.client.post(self.url, {f"quantity_{self.adult.id}": "1", "coupon_code": code})

    def test_coupon_is_priced_in_but_only_spent_once_paid(self):
        from decimal import Decimal
        from swims_orders.models import Order
        response = self.book("SWIM5")
        self.assertIn("/boipa/", response["Location"])
        order = Order.objects.get()
        self.assertEqual((order.amount, order.discount_amount), (Decimal("3.00"), Decimal("5.00")))
        self.five.refresh_from_db()
        self.assertEqual((self.five.times_used, self.five.balance_remaining), (0, Decimal("5.00")))
        self.assertNotIn("applied_coupon", self.client.session)  # not reapplied to the next swim

        order.paid = True
        order.save()
        self.five.refresh_from_db()
        self.assertEqual((self.five.times_used, self.five.balance_remaining), (1, Decimal("0.00")))

    def test_coupon_for_someone_else_is_refused_before_any_order(self):
        from swims_orders.models import Order
        response = self.book("NOTYOURS")
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertFalse(Order.objects.exists())
        self.assertNotIn("applied_coupon", self.client.session)

    def test_coupon_covering_the_swim_confirms_it_straight_away(self):
        from decimal import Decimal
        from unittest.mock import patch
        from swims_orders.models import Order
        with patch("swims.views.send_order_email"):
            response = self.book("SWIM10")
        self.assertEqual(response.status_code, 200)
        order = Order.objects.get()
        self.assertTrue(order.paid)
        self.assertEqual(order.amount, Decimal("0.00"))
        self.ten.refresh_from_db()
        self.assertEqual((self.ten.times_used, self.ten.balance_remaining), (1, Decimal("2.00")))
