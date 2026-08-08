from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from swims.models import PublicSwimCategory, PublicSwimProduct
from swims_orders.models import Order as SwimOrder

User = get_user_model()


class PublicSwimCheckInTests(TestCase):
    """The check-in on the public swim attendance page used to be a bare checkbox
    that saved nothing, so every tick was lost on refresh. These cover the state
    actually surviving, and who is allowed to change it."""

    def setUp(self):
        # create_user hardcodes is_staff=False, so promote afterwards.
        self.staff = User.objects.create_user(
            email='poolstaff@test.com', password='testpass123',
            first_name='Pool', last_name='Staff',
        )
        self.staff.is_staff = True
        self.staff.save(update_fields=['is_staff'])
        self.guardian = User.objects.create_user(
            email='swimmer@test.com', password='testpass123',
            first_name='Sam', last_name='Swimmer',
        )
        category = PublicSwimCategory.objects.create(
            name='Public Swim', slug='public-swim', description='Open swim',
        )
        product = PublicSwimProduct.objects.create(
            category=category, day_of_week=5,
            start_time=time(10, 0), end_time=time(11, 0),
            num_places=30, available=True,
        )
        self.order = SwimOrder.objects.create(
            user=self.guardian, product=product, booking=date(2026, 6, 6),
            paid=True, amount=Decimal('10.00'),
        )
        self.url = reverse('dashboard:dashboard_public_swims_check_in', args=[self.order.id])
        self.client = Client()
        self.client.force_login(self.staff)

    def test_check_in_is_saved_and_survives_a_reload(self):
        response = self.client.post(self.url, {'checked_in': '1'})
        self.assertEqual(response.status_code, 200)

        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.checked_in_at)
        self.assertEqual(self.order.checked_in_by, self.staff)

        # The page must render it back, which is the part that used to be missing.
        page = self.client.get(
            reverse('dashboard:dashboard_public_swims_attendance') + '?day=2026-06-06'
        )
        self.assertContains(page, f'id="checkin-{self.order.id}"')
        self.assertContains(page, 'Checked in')
        self.assertEqual(page.context['filtered_stats']['checked_in'], 1)

    def test_clearing_a_check_in_removes_who_and_when(self):
        self.client.post(self.url, {'checked_in': '1'})
        self.client.post(self.url, {})

        self.order.refresh_from_db()
        self.assertIsNone(self.order.checked_in_at)
        self.assertIsNone(self.order.checked_in_by)

    def test_state_is_taken_from_the_request_not_toggled(self):
        """Two check-in posts in a row must leave it checked in, so a double click
        or a replayed request cannot silently reverse a swimmer's arrival."""
        self.client.post(self.url, {'checked_in': '1'})
        self.client.post(self.url, {'checked_in': '1'})

        self.order.refresh_from_db()
        self.assertIsNotNone(self.order.checked_in_at)

    def test_non_staff_cannot_check_anyone_in(self):
        self.client.force_login(self.guardian)
        response = self.client.post(self.url, {'checked_in': '1'})

        self.assertEqual(response.status_code, 302)
        self.order.refresh_from_db()
        self.assertIsNone(self.order.checked_in_at)

    def test_get_is_rejected(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
