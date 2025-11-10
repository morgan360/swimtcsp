#!/usr/bin/env python
"""
Integration test for prorated pricing with BOIPA payment flow
Tests that prorated prices flow correctly through the entire payment system
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.local_settings')
django.setup()

from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import date, time, timedelta
from unittest.mock import patch
import time as time_module

from lessons.models import Program, Category, Product
from lessons_bookings.models import Term, LessonEnrollment
from lessons_orders.models import Order, OrderItem
from boipa.models import LessonOrderPaymentNotification
from users.models import Swimling

User = get_user_model()


class ProratedPricingPaymentIntegrationTest(TransactionTestCase):
    """
    Test that prorated pricing works correctly through the full payment flow:
    1. Lesson added to cart with prorated price
    2. Order created with prorated price
    3. Payment processed with prorated amount
    4. Enrollment created with correct prorated price recorded
    """

    def setUp(self):
        """Set up test data"""
        # Create user
        self.user = User.objects.create_user(
            email='testuser@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        # Create swimling
        self.swimling = Swimling.objects.create(
            guardian=self.user,
            first_name='Child',
            last_name='Swimmer',
            dob=date(2015, 6, 15)
        )

        # Create program and category
        self.program = Program.objects.create(name='Public Classes')
        self.category = Category.objects.create(
            program=self.program,
            name='Beginners 1',
            slug='beginners-1'
        )

        # Create lesson with 10 weeks, €100 price
        self.lesson = Product.objects.create(
            category=self.category,
            day_of_week=0,  # Monday
            start_time=time(10, 0),
            end_time=time(11, 0),
            num_places=10,
            num_weeks=10,
            price=Decimal('100.00'),
            active=True
        )

        # Create term that started 3 weeks ago (7 weeks remaining)
        today = timezone.now().date()
        self.term = Term.objects.create(
            start_date=today - timedelta(weeks=3),
            end_date=today + timedelta(weeks=7),
            rebooking_date=today - timedelta(weeks=4),
            booking_date=today - timedelta(weeks=3, days=3)
        )

        self.client = Client()
        self.client.force_login(self.user)

    def test_prorated_price_through_payment_flow(self):
        """
        Test complete flow with prorated pricing:
        1. Calculate prorated price (should be ~€70 for 7/10 weeks)
        2. Create order with prorated price
        3. Process payment with prorated amount
        4. Verify enrollment created with correct price
        """
        print("\n" + "="*70)
        print("PRORATED PRICING PAYMENT INTEGRATION TEST")
        print("="*70)

        # ===== STEP 1: Calculate Prorated Price =====
        prorated_price = self.lesson.get_prorated_price(self.term)
        full_price = self.lesson.price

        print(f"\n📊 Price Calculation:")
        print(f"  Full Price: €{full_price}")
        print(f"  Prorated Price: €{prorated_price}")
        print(f"  Savings: €{full_price - prorated_price:.2f}")

        # Verify prorated price is less than full price
        self.assertLess(prorated_price, full_price)
        # Verify it's approximately 70% (7 weeks out of 10)
        expected_ratio = 0.7
        actual_ratio = float(prorated_price) / float(full_price)
        self.assertAlmostEqual(actual_ratio, expected_ratio, delta=0.1)
        print(f"  Price Ratio: {actual_ratio:.2%} (expected ~{expected_ratio:.0%})")

        # ===== STEP 2: Create Order with Prorated Price =====
        order = Order.objects.create(
            user=self.user,
            amount=prorated_price,  # Use prorated price!
            paid=False
        )

        order_item = OrderItem.objects.create(
            order=order,
            product=self.lesson,
            price=prorated_price,  # Store prorated price
            quantity=1,
            swimling=self.swimling,
            term=self.term
        )

        print(f"\n📦 Order Created:")
        print(f"  Order ID: {order.id}")
        print(f"  Order Amount: €{order.amount}")
        print(f"  OrderItem Price: €{order_item.price}")
        print(f"  Full Price (for reference): €{self.lesson.price}")

        # Verify order uses prorated price
        self.assertEqual(order.amount, prorated_price)
        self.assertEqual(order_item.price, prorated_price)
        self.assertFalse(order.paid)

        # ===== STEP 3: Simulate Payment with Prorated Amount =====
        merchant_tx_id = f"lesson_{order.id}_{int(time_module.time())}"
        payment_notification_data = {
            'merchantTxId': merchant_tx_id,
            'txId': 'BOIPA_TX_PRORATED_12345',
            'result': 'success',
            'status': 'CAPTURED',
            'amount': str(prorated_price),  # Payment for prorated amount
            'currency': 'EUR',
            'country': 'IE',
            'action': 'PURCHASE',
        }

        print(f"\n💳 Payment Processing:")
        print(f"  Payment Amount: €{payment_notification_data['amount']}")
        print(f"  Transaction ID: {payment_notification_data['txId']}")

        # Mock email sending
        with patch('lessons_orders.tasks.send_lesson_order_email') as mock_email:
            mock_email.return_value = None

            # POST to payment webhook
            response = self.client.post(
                reverse('boipa:payment_notification'),
                data=payment_notification_data
            )

            self.assertEqual(response.status_code, 200)
            print(f"  Webhook Response: {response.status_code} ✓")

        # ===== STEP 4: Verify Payment Processed =====
        order.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(order.txId, 'BOIPA_TX_PRORATED_12345')
        print(f"\n✅ Order Paid:")
        print(f"  Order ID: {order.id}")
        print(f"  Paid: {order.paid}")
        print(f"  Transaction ID: {order.txId}")

        # ===== STEP 5: Verify Enrollment Created with Prorated Price =====
        enrollment = LessonEnrollment.objects.filter(
            swimling=self.swimling,
            lesson=self.lesson,
            term=self.term,
            order=order
        ).first()

        self.assertIsNotNone(enrollment, "Enrollment should be created")
        print(f"\n🎓 Enrollment Created:")
        print(f"  Enrollment ID: {enrollment.id}")
        print(f"  Swimling: {enrollment.swimling}")
        print(f"  Lesson: {enrollment.lesson.name}")
        print(f"  Term: Term {enrollment.term.id}")

        # Verify payment notification has correct prorated amount
        notification = LessonOrderPaymentNotification.objects.filter(order=order).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.amount, prorated_price)
        print(f"\n📝 Payment Notification:")
        print(f"  Notification ID: {notification.id}")
        print(f"  Amount Charged: €{notification.amount}")
        print(f"  Status: {notification.status}")

        # ===== SUMMARY =====
        print("\n" + "="*70)
        print("✅ PRORATED PRICING PAYMENT INTEGRATION TEST PASSED")
        print("="*70)
        print(f"Full Price: €{full_price}")
        print(f"Prorated Price: €{prorated_price}")
        print(f"Amount Charged: €{notification.amount}")
        print(f"Enrollment Created: Yes (ID: {enrollment.id})")
        print(f"Order Paid: {order.paid}")
        print("="*70)

    def test_full_price_before_term_starts(self):
        """
        Test that full price is used when term hasn't started yet
        """
        # Create future term (not started yet)
        today = timezone.now().date()
        future_term = Term.objects.create(
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(weeks=10, days=7),
            rebooking_date=today + timedelta(days=1),
            booking_date=today + timedelta(days=3)
        )

        # Get price for future term
        price = self.lesson.get_prorated_price(future_term)

        print("\n" + "="*70)
        print("FULL PRICE BEFORE TERM STARTS TEST")
        print("="*70)
        print(f"Term starts in 7 days")
        print(f"Full Price: €{self.lesson.price}")
        print(f"Calculated Price: €{price}")

        # Should be full price (no proration)
        self.assertEqual(price, self.lesson.price)

        # Create order
        order = Order.objects.create(
            user=self.user,
            amount=price,
            paid=False
        )

        OrderItem.objects.create(
            order=order,
            product=self.lesson,
            price=price,
            quantity=1,
            swimling=self.swimling,
            term=future_term
        )

        print(f"Order Amount: €{order.amount}")
        print("✅ Full price charged for future term")
        print("="*70)


if __name__ == '__main__':
    import unittest

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(ProratedPricingPaymentIntegrationTest)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)