from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from lessons.models import Product, Category, Program
from lessons_bookings.models import Term


class ProratedPricingTestCase(TestCase):
    """Test cases for the prorated pricing functionality"""

    def setUp(self):
        """Set up test data"""
        # Create a program and category
        self.program = Program.objects.create(name="Test Program")
        self.category = Category.objects.create(
            name="Beginners 1",
            program=self.program
        )

        # Create a product (lesson) with 10 weeks and €100 price
        self.product = Product.objects.create(
            category=self.category,
            day_of_week=0,  # Monday
            num_places=10,
            num_weeks=10,
            price=Decimal('100.00'),
            active=True
        )

    def test_full_price_before_term_starts(self):
        """Test that full price is charged when term hasn't started yet"""
        today = timezone.now().date()
        future_start = today + timedelta(days=7)
        future_end = future_start + timedelta(weeks=10)

        term = Term.objects.create(
            start_date=future_start,
            end_date=future_end,
            rebooking_date=today + timedelta(days=1),
            booking_date=today + timedelta(days=3)
        )

        prorated_price = self.product.get_prorated_price(term)
        self.assertEqual(prorated_price, Decimal('100.00'))

    def test_prorated_price_after_term_starts(self):
        """Test that price is prorated after term starts"""
        today = timezone.now().date()
        # Term started 3 weeks ago (30% of 10 weeks passed)
        # So 7 weeks remain (70% of term)
        past_start = today - timedelta(weeks=3)
        future_end = today + timedelta(weeks=7)

        term = Term.objects.create(
            start_date=past_start,
            end_date=future_end,
            rebooking_date=past_start - timedelta(days=7),
            booking_date=past_start - timedelta(days=3)
        )

        prorated_price = self.product.get_prorated_price(term)
        # Should be approximately €70.00 (7 weeks remaining out of 10)
        # Allow small variance due to fractional days
        self.assertAlmostEqual(float(prorated_price), 70.00, delta=10.00)

    def test_minimum_one_week_price(self):
        """Test that minimum charge is at least one week's price"""
        today = timezone.now().date()
        # Term started 9.5 weeks ago, only 0.5 weeks remain
        past_start = today - timedelta(weeks=9, days=3)
        future_end = today + timedelta(days=4)

        term = Term.objects.create(
            start_date=past_start,
            end_date=future_end,
            rebooking_date=past_start - timedelta(days=7),
            booking_date=past_start - timedelta(days=3)
        )

        prorated_price = self.product.get_prorated_price(term)
        expected_min_price = Decimal('100.00') / Decimal('10')  # €10 per week

        # Should charge at least one week's price
        self.assertGreaterEqual(prorated_price, expected_min_price)

    def test_zero_price_after_term_ends(self):
        """Test that price is zero after term has ended"""
        today = timezone.now().date()
        past_start = today - timedelta(weeks=12)
        past_end = today - timedelta(days=1)

        term = Term.objects.create(
            start_date=past_start,
            end_date=past_end,
            rebooking_date=past_start - timedelta(days=7),
            booking_date=past_start - timedelta(days=3)
        )

        prorated_price = self.product.get_prorated_price(term)
        self.assertEqual(prorated_price, Decimal('0.00'))

    def test_midterm_pricing(self):
        """Test pricing calculation at exactly mid-term"""
        today = timezone.now().date()
        # Term started 5 weeks ago, 5 weeks remain
        past_start = today - timedelta(weeks=5)
        future_end = today + timedelta(weeks=5)

        term = Term.objects.create(
            start_date=past_start,
            end_date=future_end,
            rebooking_date=past_start - timedelta(days=7),
            booking_date=past_start - timedelta(days=3)
        )

        prorated_price = self.product.get_prorated_price(term)
        # Should be approximately €50.00 (5 weeks out of 10 remaining)
        self.assertAlmostEqual(float(prorated_price), 50.00, delta=5.00)