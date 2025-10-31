from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from datetime import date, time, timedelta
from unittest.mock import patch, MagicMock
import time as time_module

from lessons.models import Program, Category, Product
from lessons_bookings.models import Term, LessonEnrollment
from lessons_orders.models import Order, OrderItem
from boipa.models import LessonOrderPaymentNotification
from users.models import Swimling

User = get_user_model()


class LessonOrderBOIPAIntegrationTest(TransactionTestCase):
    """
    Integration test for lesson order payment flow using BOIPA sandbox.
    Tests the complete flow from order creation to payment confirmation and enrollment.

    KEY DIFFERENCE FROM SWIM ORDERS:
    - Lesson orders create LessonEnrollment records after successful payment
    - Requires Term, Swimling, and Lesson (Product) associations
    """

    def setUp(self):
        """Set up test data for lesson order testing"""
        # Create test user (guardian)
        self.user = User.objects.create_user(
            email='testparent@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Parent'
        )

        # Create swimling (child who will be enrolled)
        self.swimling = Swimling.objects.create(
            guardian=self.user,
            first_name='Child',
            last_name='Student',
            dob=date(2015, 6, 15)
        )

        # Create program and category
        self.program = Program.objects.create(
            name='Public Classes'
        )

        self.category = Category.objects.create(
            program=self.program,
            name='Beginners 1',
            slug='beginners-1',
            stage='Stage 1'
        )

        # Create lesson (Product)
        self.lesson = Product.objects.create(
            category=self.category,
            day_of_week=0,  # Monday
            start_time=time(10, 0),
            end_time=time(11, 0),
            num_places=10,
            num_weeks=8,
            price=Decimal('80.00'),
            active=True
        )

        # Create term (CRITICAL - required for enrollment)
        today = timezone.now().date()
        self.term = Term.objects.create(
            start_date=today,
            end_date=today + timedelta(days=56),  # 8 weeks
            rebooking_date=today - timedelta(days=7),
            booking_date=today - timedelta(days=5),
            assessment_date=today + timedelta(days=57)
        )

        # Initialize test client
        self.client = Client()
        self.client.force_login(self.user)

    def test_lesson_order_complete_payment_flow_with_enrollment(self):
        """
        Test complete lesson order flow:
        1. Create order with OrderItem (including term)
        2. Simulate BOIPA payment notification webhook
        3. Verify order marked as paid
        4. Verify payment notification record created
        5. **Verify LessonEnrollment created** (key difference from swims)
        """
        # ===== STEP 1: Create Order =====
        order = Order.objects.create(
            user=self.user,
            amount=Decimal('80.00'),
            paid=False
        )

        # Create order item (with term - CRITICAL for enrollment)
        order_item = OrderItem.objects.create(
            order=order,
            product=self.lesson,
            price=self.lesson.price,
            quantity=1,
            swimling=self.swimling,
            term=self.term  # MUST be set for enrollment to work
        )

        # Verify order created correctly
        self.assertEqual(order.user, self.user)
        self.assertFalse(order.paid)
        self.assertEqual(order.amount, Decimal('80.00'))
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.get_total_cost(), Decimal('80.00'))
        self.assertEqual(order_item.term, self.term)
        self.assertEqual(order_item.swimling, self.swimling)
        print(f"✓ Order created: Order ID {order.id}, Amount €{order.amount}")

        # Verify NO enrollment exists yet (order not paid)
        enrollments_before = LessonEnrollment.objects.filter(
            swimling=self.swimling,
            lesson=self.lesson,
            term=self.term
        )
        self.assertEqual(enrollments_before.count(), 0)
        print("✓ No enrollment exists before payment")

        # ===== STEP 2: Simulate BOIPA Token Generation (Mock) =====
        with patch('boipa.payment_functions.get_boipa_session_token') as mock_token:
            mock_token.return_value = {
                'token': 'test_boipa_token_12345',
                'timestamp': int(time_module.time() * 1000)
            }

            # Generate merchantTxId (same format as production)
            merchant_tx_id = f"lesson_{order.id}_{int(time_module.time())}"
            print(f"✓ Mock BOIPA token generated: {merchant_tx_id}")

        # ===== STEP 3: Simulate BOIPA Payment Notification Webhook =====
        payment_notification_data = {
            'merchantTxId': merchant_tx_id,
            'txId': 'BOIPA_TX_LESSON_12345',
            'result': 'success',
            'status': 'CAPTURED',
            'amount': '80.00',
            'currency': 'EUR',
            'country': 'IE',
            'action': 'PURCHASE',
            'auth_code': 'AUTH123',
            'acquirer': 'TEST_ACQUIRER',
            'acquirerAmount': '80.00',
            'merchantId': settings.BOIPA_MERCHANT_ID,
            'brandId': '1',
            'customerId': str(self.user.id),
            'acquirerCurrency': 'EUR',
            'paymentSolutionId': '500',
        }

        # Mock email sending and enrollment function
        with patch('lessons_orders.tasks.send_lesson_order_email') as mock_email:
            mock_email.return_value = None

            # POST to payment notification webhook
            response = self.client.post(
                reverse('boipa:payment_notification'),
                data=payment_notification_data
            )

            # Verify webhook accepted the payment
            self.assertEqual(response.status_code, 200)
            print(f"✓ BOIPA webhook processed: {response.status_code}")

        # ===== STEP 4: Verify Order Marked as Paid =====
        order.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(order.txId, 'BOIPA_TX_LESSON_12345')
        print(f"✓ Order marked as PAID: Order {order.id}, txId={order.txId}")

        # ===== STEP 5: Verify Payment Notification Record Created =====
        notification = LessonOrderPaymentNotification.objects.filter(order=order).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.txId, 'BOIPA_TX_LESSON_12345')
        self.assertEqual(notification.merchantTxId, merchant_tx_id)
        self.assertEqual(notification.status, 'CAPTURED')
        self.assertEqual(notification.amount, Decimal('80.00'))
        self.assertEqual(notification.currency, 'EUR')
        print(f"✓ Payment notification record created: {notification.id}")

        # ===== STEP 6: Verify LessonEnrollment Created (KEY TEST!) =====
        enrollment = LessonEnrollment.objects.filter(
            swimling=self.swimling,
            lesson=self.lesson,
            term=self.term,
            order=order
        ).first()

        self.assertIsNotNone(enrollment, "Enrollment should be created after successful payment")
        self.assertEqual(enrollment.swimling, self.swimling)
        self.assertEqual(enrollment.lesson, self.lesson)
        self.assertEqual(enrollment.term, self.term)
        self.assertEqual(enrollment.order, order)
        print(f"✓ LessonEnrollment created: {enrollment.id}")
        print(f"  - Swimling: {enrollment.swimling}")
        print(f"  - Lesson: {enrollment.lesson.name}")
        print(f"  - Term: {enrollment.term.id}")

        # ===== STEP 7: Test Idempotency (Duplicate Webhook) =====
        with patch('lessons_orders.tasks.send_lesson_order_email') as mock_email_2:
            mock_email_2.return_value = None

            response_2 = self.client.post(
                reverse('boipa:payment_notification'),
                data=payment_notification_data
            )

            # Should still return 200 but not process again
            self.assertEqual(response_2.status_code, 200)
            print("✓ Duplicate notification handled (idempotent)")

        # Verify only ONE enrollment exists (no duplicates)
        enrollment_count = LessonEnrollment.objects.filter(
            swimling=self.swimling,
            lesson=self.lesson,
            term=self.term
        ).count()
        self.assertEqual(enrollment_count, 1)
        print("✓ Only one enrollment exists (no duplicates)")

        # Verify only ONE notification record exists
        notification_count = LessonOrderPaymentNotification.objects.filter(order=order).count()
        self.assertEqual(notification_count, 1)
        print("✓ Only one notification record exists")

        print("\n" + "="*60)
        print("✅ LESSON ORDER PAYMENT FLOW WITH ENROLLMENT TEST PASSED")
        print("="*60)
        print(f"Order ID: {order.id}")
        print(f"Product: {order.items.first().product.name}")
        print(f"Amount: €{order.amount}")
        print(f"Paid: {order.paid}")
        print(f"Transaction ID: {order.txId}")
        print(f"Enrollment ID: {enrollment.id}")
        print(f"Enrollment: {enrollment.swimling} → {enrollment.lesson.category.name}")
        print("="*60)

    def test_lesson_order_failed_payment_no_enrollment(self):
        """
        Test that failed payment does NOT create enrollment
        """
        # Create order
        order = Order.objects.create(
            user=self.user,
            amount=Decimal('80.00'),
            paid=False
        )

        OrderItem.objects.create(
            order=order,
            product=self.lesson,
            price=self.lesson.price,
            quantity=1,
            swimling=self.swimling,
            term=self.term
        )

        # Simulate failed payment notification
        merchant_tx_id = f"lesson_{order.id}_{int(time_module.time())}"
        failed_payment_data = {
            'merchantTxId': merchant_tx_id,
            'txId': 'BOIPA_TX_FAILED_99999',
            'result': 'failure',
            'status': 'DECLINED',
            'amount': '80.00',
            'currency': 'EUR',
            'country': 'IE',
            'errorMessage': 'Card declined',
        }

        with patch('lessons_orders.tasks.send_lesson_order_email') as mock_email:
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
        self.assertEqual(order.txId, '')
        print(f"✓ Failed payment handled: Order {order.id} remains unpaid")

        # Verify notification record created with failure details
        notification = LessonOrderPaymentNotification.objects.filter(order=order).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.status, 'DECLINED')
        self.assertEqual(notification.errorMessage, 'Card declined')
        print(f"✓ Failed payment notification recorded: {notification.id}")

        # **KEY TEST:** Verify NO enrollment created for failed payment
        enrollment_count = LessonEnrollment.objects.filter(
            swimling=self.swimling,
            lesson=self.lesson,
            term=self.term
        ).count()
        self.assertEqual(enrollment_count, 0)
        print("✓ NO enrollment created for failed payment")

        print("\n" + "="*60)
        print("✅ FAILED PAYMENT NO ENROLLMENT TEST PASSED")
        print("="*60)

    def test_lesson_order_multiple_swimlings(self):
        """
        Test order with multiple children (multiple enrollments)
        Common scenario: Parent books 2 siblings for the same lesson
        """
        # Create second swimling (sibling)
        sibling = Swimling.objects.create(
            guardian=self.user,
            first_name='Sibling',
            last_name='Student',
            dob=date(2017, 3, 20)
        )

        # Create order with 2 children
        order = Order.objects.create(
            user=self.user,
            amount=Decimal('160.00'),  # 2 x €80
            paid=False
        )

        # Create order items for both children
        OrderItem.objects.create(
            order=order,
            product=self.lesson,
            price=self.lesson.price,
            quantity=1,
            swimling=self.swimling,
            term=self.term
        )

        OrderItem.objects.create(
            order=order,
            product=self.lesson,
            price=self.lesson.price,
            quantity=1,
            swimling=sibling,
            term=self.term
        )

        # Verify order items
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.get_total_cost(), Decimal('160.00'))
        print(f"✓ Multi-child order created: {order.items.count()} children, €{order.get_total_cost()}")

        # Simulate successful payment
        merchant_tx_id = f"lesson_{order.id}_{int(time_module.time())}"
        payment_data = {
            'merchantTxId': merchant_tx_id,
            'txId': 'BOIPA_TX_MULTI_55555',
            'result': 'success',
            'status': 'CAPTURED',
            'amount': '160.00',
            'currency': 'EUR',
            'country': 'IE',
        }

        with patch('lessons_orders.tasks.send_lesson_order_email'):
            response = self.client.post(
                reverse('boipa:payment_notification'),
                data=payment_data
            )
            self.assertEqual(response.status_code, 200)

        # Verify payment processed
        order.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(order.txId, 'BOIPA_TX_MULTI_55555')
        print(f"✓ Multi-child order paid: Order {order.id}")

        # **KEY TEST:** Verify BOTH enrollments created
        enrollments = LessonEnrollment.objects.filter(
            lesson=self.lesson,
            term=self.term,
            order=order
        ).order_by('swimling__first_name')

        self.assertEqual(enrollments.count(), 2)
        print(f"✓ Created {enrollments.count()} enrollments for {order.items.count()} children")

        # Verify first child enrolled
        child1_enrollment = enrollments.filter(swimling=self.swimling).first()
        self.assertIsNotNone(child1_enrollment)
        self.assertEqual(child1_enrollment.swimling, self.swimling)
        print(f"  - Child 1 enrolled: {child1_enrollment.swimling.first_name}")

        # Verify second child enrolled
        child2_enrollment = enrollments.filter(swimling=sibling).first()
        self.assertIsNotNone(child2_enrollment)
        self.assertEqual(child2_enrollment.swimling, sibling)
        print(f"  - Child 2 enrolled: {child2_enrollment.swimling.first_name}")

        print("\n" + "="*60)
        print("✅ MULTI-CHILD ENROLLMENT TEST PASSED")
        print("="*60)