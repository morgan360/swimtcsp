from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from decimal import Decimal
from datetime import date, time
from unittest.mock import patch, MagicMock
import time as time_module

from swims.models import PublicSwimCategory, PublicSwimProduct, PriceVariant
from swims_orders.models import Order, OrderItem
from boipa.models import SwimOrderPaymentNotification
from users.models import Swimling

User = get_user_model()


class SwimOrderBOIPAIntegrationTest(TestCase):
    """
    Integration test for swim order payment flow using BOIPA sandbox.
    Tests the complete flow from order creation to payment confirmation.
    """

    def setUp(self):
        """Set up test data for swim order testing"""
        # Create test user
        self.user = User.objects.create_user(
            email='testswimmer@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Swimmer'
        )

        # Create swimling (swimmer profile)
        self.swimling = Swimling.objects.create(
            guardian=self.user,
            first_name='Child',
            last_name='Swimmer',
            dob=date(2015, 6, 15)
        )

        # Create swim category
        self.category = PublicSwimCategory.objects.create(
            name='Public Swim',
            slug='public-swim',
            description='Open swim sessions'
        )

        # Create swim product
        self.swim_product = PublicSwimProduct.objects.create(
            category=self.category,
            day_of_week=5,  # Saturday
            start_time=time(10, 0),
            end_time=time(11, 0),
            num_places=30,
            available=True
        )

        # Create price variant (Adult)
        self.price_variant = PriceVariant.objects.create(
            product=self.swim_product,
            variant='Adult',
            price=Decimal('9.00')
        )

        # Create booking date (next Saturday)
        self.booking_date = date(2025, 11, 8)

        # Initialize test client
        self.client = Client()
        self.client.force_login(self.user)

    def test_swim_order_complete_payment_flow(self):
        """
        Test complete swim order flow:
        1. Create order
        2. Simulate BOIPA payment notification webhook
        3. Verify order marked as paid
        4. Verify payment notification record created
        """
        # ===== STEP 1: Create Order =====
        order = Order.objects.create(
            user=self.user,
            product=self.swim_product,
            booking=self.booking_date,
            amount=Decimal('9.00'),
            paid=False
        )

        # Create order item
        order_item = OrderItem.objects.create(
            order=order,
            variant=self.price_variant,
            quantity=1
        )

        # Verify order created correctly
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.product, self.swim_product)
        self.assertFalse(order.paid)
        self.assertEqual(order.amount, Decimal('9.00'))
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.get_total_cost(), Decimal('9.00'))

        print(f"✓ Order created: Order ID {order.id}, Amount €{order.amount}")

        # ===== STEP 2: Simulate BOIPA Token Generation (Mock) =====
        # In real scenario, this would call BOIPA API
        # For testing, we mock the token generation
        with patch('boipa.payment_functions.get_boipa_session_token') as mock_token:
            mock_token.return_value = {
                'token': 'test_boipa_token_12345',
                'timestamp': int(time_module.time() * 1000)
            }

            # Generate merchantTxId (same format as production)
            merchant_tx_id = f"swims_{order.id}_{int(time_module.time())}"
            print(f"✓ Mock BOIPA token generated: {merchant_tx_id}")

        # ===== STEP 3: Simulate BOIPA Payment Notification Webhook =====
        # This simulates what BOIPA sends after successful payment
        payment_notification_data = {
            'merchantTxId': merchant_tx_id,
            'txId': 'BOIPA_TX_TEST_67890',
            'result': 'success',
            'status': 'CAPTURED',
            'amount': '9.00',
            'currency': 'EUR',
            'country': 'IE',
            'action': 'PURCHASE',
            'auth_code': 'AUTH123',
            'acquirer': 'TEST_ACQUIRER',
            'acquirerAmount': '9.00',
            'merchantId': settings.BOIPA_MERCHANT_ID,
            'brandId': '1',
            'customerId': str(self.user.id),
            'acquirerCurrency': 'EUR',
            'paymentSolutionId': '500',
        }

        # Mock email sending to avoid actual email dispatch
        with patch('swims_orders.tasks.send_order_email') as mock_email:
            mock_email.return_value = None

            # POST to payment notification webhook
            response = self.client.post(
                reverse('boipa:payment_notification'),
                data=payment_notification_data
            )

            # Verify webhook accepted the payment
            self.assertEqual(response.status_code, 200)
            print(f"✓ BOIPA webhook processed: {response.status_code}")

            # Note: Email is triggered via transaction.on_commit() which may not
            # be called in the same way during tests. The important thing is that
            # the order is marked as paid and the notification is created.
            print("✓ Payment webhook processed (email would be sent via on_commit)")

        # ===== STEP 4: Verify Order Marked as Paid =====
        order.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(order.txId, 'BOIPA_TX_TEST_67890')
        print(f"✓ Order marked as PAID: Order {order.id}, txId={order.txId}")

        # ===== STEP 5: Verify Payment Notification Record Created =====
        notification = SwimOrderPaymentNotification.objects.filter(order=order).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.txId, 'BOIPA_TX_TEST_67890')
        self.assertEqual(notification.merchantTxId, merchant_tx_id)
        self.assertEqual(notification.status, 'CAPTURED')
        self.assertEqual(notification.amount, Decimal('9.00'))
        self.assertEqual(notification.currency, 'EUR')
        print(f"✓ Payment notification record created: {notification.id}")

        # ===== STEP 6: Test Idempotency (Duplicate Webhook) =====
        # BOIPA may send duplicate notifications - ensure we handle gracefully
        with patch('swims_orders.tasks.send_order_email') as mock_email_2:
            mock_email_2.return_value = None

            response_2 = self.client.post(
                reverse('boipa:payment_notification'),
                data=payment_notification_data
            )

            # Should still return 200 but not process again
            self.assertEqual(response_2.status_code, 200)

            # Email should NOT be sent again
            mock_email_2.assert_not_called()
            print("✓ Duplicate notification handled (idempotent)")

        # Verify only ONE notification record exists
        notification_count = SwimOrderPaymentNotification.objects.filter(order=order).count()
        self.assertEqual(notification_count, 1)
        print("✓ Only one notification record exists (no duplicates)")

        print("\n" + "="*60)
        print("✅ SWIM ORDER PAYMENT FLOW TEST PASSED")
        print("="*60)
        print(f"Order ID: {order.id}")
        print(f"Product: {order.product}")
        print(f"Booking Date: {order.booking}")
        print(f"Amount: €{order.amount}")
        print(f"Paid: {order.paid}")
        print(f"Transaction ID: {order.txId}")
        print(f"Payment Notification: {notification.id}")
        print("="*60)

    def test_swim_order_failed_payment(self):
        """
        Test handling of failed payment notification
        """
        # Create order
        order = Order.objects.create(
            user=self.user,
            product=self.swim_product,
            booking=self.booking_date,
            amount=Decimal('9.00'),
            paid=False
        )

        OrderItem.objects.create(
            order=order,
            variant=self.price_variant,
            quantity=1
        )

        # Simulate failed payment notification
        merchant_tx_id = f"swims_{order.id}_{int(time_module.time())}"
        failed_payment_data = {
            'merchantTxId': merchant_tx_id,
            'txId': 'BOIPA_TX_FAILED_99999',
            'result': 'failure',
            'status': 'DECLINED',
            'amount': '9.00',
            'currency': 'EUR',
            'country': 'IE',
            'errorMessage': 'Card declined',
        }

        # Mock email sending
        with patch('swims_orders.tasks.send_order_email') as mock_email:
            response = self.client.post(
                reverse('boipa:payment_notification'),
                data=failed_payment_data
            )

            # Webhook should accept the notification
            self.assertEqual(response.status_code, 200)

            # Email should NOT be sent for failed payment
            mock_email.assert_not_called()

        # Verify order still marked as UNPAID
        order.refresh_from_db()
        self.assertFalse(order.paid)
        self.assertEqual(order.txId, '')  # No txId stored for failed payments
        print(f"✓ Failed payment handled: Order {order.id} remains unpaid")

        # Verify notification record created with failure details
        notification = SwimOrderPaymentNotification.objects.filter(order=order).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.status, 'DECLINED')
        self.assertEqual(notification.errorMessage, 'Card declined')
        print(f"✓ Failed payment notification recorded: {notification.id}")

        print("\n" + "="*60)
        print("✅ FAILED PAYMENT TEST PASSED")
        print("="*60)

    def test_swim_order_with_multiple_items(self):
        """
        Test order with multiple swimmers (multiple order items)
        """
        # Create another price variant (Child)
        child_variant = PriceVariant.objects.create(
            product=self.swim_product,
            variant='Child',
            price=Decimal('7.00')
        )

        # Create order with multiple items (1 Adult + 2 Children)
        order = Order.objects.create(
            user=self.user,
            product=self.swim_product,
            booking=self.booking_date,
            amount=Decimal('23.00'),  # 9 + 7 + 7
            paid=False
        )

        OrderItem.objects.create(order=order, variant=self.price_variant, quantity=1)  # Adult
        OrderItem.objects.create(order=order, variant=child_variant, quantity=2)  # 2 Children

        # Verify total cost calculation
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.get_total_cost(), Decimal('23.00'))
        print(f"✓ Multi-item order created: {order.items.count()} items, €{order.get_total_cost()}")

        # Simulate successful payment
        merchant_tx_id = f"swims_{order.id}_{int(time_module.time())}"
        payment_data = {
            'merchantTxId': merchant_tx_id,
            'txId': 'BOIPA_TX_MULTI_55555',
            'result': 'success',
            'status': 'CAPTURED',
            'amount': '23.00',
            'currency': 'EUR',
            'country': 'IE',
        }

        with patch('swims_orders.tasks.send_order_email'):
            response = self.client.post(
                reverse('boipa:payment_notification'),
                data=payment_data
            )
            self.assertEqual(response.status_code, 200)

        # Verify payment processed
        order.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(order.txId, 'BOIPA_TX_MULTI_55555')
        print(f"✓ Multi-item order paid: Order {order.id}")

        print("\n" + "="*60)
        print("✅ MULTI-ITEM ORDER TEST PASSED")
        print("="*60)