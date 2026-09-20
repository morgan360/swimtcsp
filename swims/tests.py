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
        url = reverse('swimsadmin:swims_pricevariant_changelist')
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
