from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
from datetime import date, time, timedelta
from unittest.mock import patch, MagicMock
import time as time_module

from schools.models import ScoSchool, ScoProgram, ScoCategory, ScoLessons
from schools_bookings.models import ScoTerm, ScoEnrollment
from schools_orders.models import Order, OrderItem
from boipa.models import SchoolOrderPaymentNotification
from users.models import Swimling

User = get_user_model()


class SchoolOrderBOIPAIntegrationTest(TransactionTestCase):
    """
    Integration test for school order payment flow using BOIPA sandbox.
    Tests the complete flow from order creation to payment confirmation and enrollment.

    KEY DIFFERENCES FROM PUBLIC LESSONS:
    - Uses ScoTerm (school-specific terms) instead of Term
    - Uses ScoLessons instead of Product
    - Creates ScoEnrollment instead of LessonEnrollment
    - Order has direct 'school' foreign key
    """

    def setUp(self):
        """Set up test data for school order testing"""
        # Create test user (guardian/school admin)
        self.user = User.objects.create_user(
            email='schooladmin@test.com',
            password='testpass123',
            first_name='School',
            last_name='Admin'
        )

        # Create swimling (child who will be enrolled)
        self.swimling = Swimling.objects.create(
            guardian=self.user,
            first_name='School',
            last_name='Student',
            dob=date(2015, 6, 15),
            sco_role_num='STU001'  # School roll number
        )

        # Create school
        self.school = ScoSchool.objects.create(
            name='Test Primary School',
            sco_role_num='SCH001',
            email='school@test.ie',
            phone='012345678'
        )

        # Create program and category
        self.program = ScoProgram.objects.create(
            name='School Swimming Program'
        )

        self.category = ScoCategory.objects.create(
            program=self.program,
            name='Water Safety Level 1',
            slug='water-safety-1'
        )

        # Create school lesson (ScoLessons)
        self.sco_lesson = ScoLessons.objects.create(
            category=self.category,
            school=self.school,
            day_of_week=2,  # Wednesday
            start_time=time(14, 0),
            end_time=time(15, 0),
            num_places=25,
            num_weeks=12,
            price=Decimal('150.00'),
            active=True
        )

        # Create school term (ScoTerm - CRITICAL for enrollment)
        today = timezone.now().date()
        self.sco_term = ScoTerm.objects.create(
            school=self.school,
            start_date=today,
            end_date=today + timedelta(days=84),  # 12 weeks
            booking_start_date=today - timedelta(days=14),
            booking_end_date=today + timedelta(days=7),
            assessment_date=today + timedelta(days=85),
            is_active=True
        )

        # Initialize test client
        self.client = Client()
        self.client.force_login(self.user)

    def test_school_order_complete_payment_flow_with_enrollment(self):
        """
        Test complete school order flow:
        1. Create order with OrderItem (including ScoTerm)
        2. Simulate BOIPA payment notification webhook
        3. Verify order marked as paid
        4. Verify payment notification record created
        5. **Verify ScoEnrollment created** (key test)
        """
        # ===== STEP 1: Create Order =====
        order = Order.objects.create(
            user=self.user,
            school=self.school,  # School orders have direct school FK
            amount=Decimal('150.00'),
            paid=False
        )

        # Create order item (with ScoTerm - CRITICAL for enrollment)
        order_item = OrderItem.objects.create(
            order=order,
            product=self.sco_lesson,
            price=self.sco_lesson.price,
            quantity=1,
            swimling=self.swimling,
            term=self.sco_term  # MUST be set for enrollment to work
        )

        # Verify order created correctly
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.school, self.school)
        self.assertFalse(order.paid)
        self.assertEqual(order.amount, Decimal('150.00'))
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order_item.term, self.sco_term)
        self.assertEqual(order_item.swimling, self.swimling)
        print(f"✓ School order created: Order ID {order.id}, Amount €{order.amount}")

        # Verify NO enrollment exists yet (order not paid)
        enrollments_before = ScoEnrollment.objects.filter(
            swimling=self.swimling,
            lesson=self.sco_lesson,
            term=self.sco_term
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
            merchant_tx_id = f"school_{order.id}_{int(time_module.time())}"
            print(f"✓ Mock BOIPA token generated: {merchant_tx_id}")

        # ===== STEP 3: Simulate BOIPA Payment Notification Webhook =====
        payment_notification_data = {
            'merchantTxId': merchant_tx_id,
            'txId': 'BOIPA_TX_SCHOOL_12345',
            'result': 'success',
            'status': 'CAPTURED',
            'amount': '150.00',
            'currency': 'EUR',
            'country': 'IE',
            'action': 'PURCHASE',
            'auth_code': 'AUTH123',
            'acquirer': 'TEST_ACQUIRER',
            'acquirerAmount': '150.00',
            'merchantId': settings.BOIPA_MERCHANT_ID,
            'brandId': '1',
            'customerId': str(self.user.id),
            'acquirerCurrency': 'EUR',
            'paymentSolutionId': '500',
        }

        # Mock email sending
        with patch('schools_orders.tasks.send_school_order_email') as mock_email:
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
        self.assertEqual(order.txId, 'BOIPA_TX_SCHOOL_12345')
        print(f"✓ Order marked as PAID: Order {order.id}, txId={order.txId}")

        # ===== STEP 5: Verify Payment Notification Record Created =====
        notification = SchoolOrderPaymentNotification.objects.filter(order=order).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.txId, 'BOIPA_TX_SCHOOL_12345')
        self.assertEqual(notification.merchantTxId, merchant_tx_id)
        self.assertEqual(notification.status, 'CAPTURED')
        self.assertEqual(notification.amount, Decimal('150.00'))
        self.assertEqual(notification.currency, 'EUR')
        print(f"✓ Payment notification record created: {notification.id}")

        # ===== STEP 6: Verify ScoEnrollment Created (KEY TEST!) =====
        enrollment = ScoEnrollment.objects.filter(
            swimling=self.swimling,
            lesson=self.sco_lesson,
            term=self.sco_term,
            order=order
        ).first()

        self.assertIsNotNone(enrollment, "ScoEnrollment should be created after successful payment")
        self.assertEqual(enrollment.swimling, self.swimling)
        self.assertEqual(enrollment.lesson, self.sco_lesson)
        self.assertEqual(enrollment.term, self.sco_term)
        self.assertEqual(enrollment.order, order)
        print(f"✓ ScoEnrollment created: {enrollment.id}")
        print(f"  - Swimling: {enrollment.swimling}")
        print(f"  - Lesson: {enrollment.lesson.name}")
        print(f"  - Term: Term {enrollment.term.id} ({enrollment.term.school.name})")

        # ===== STEP 7: Test Idempotency (Duplicate Webhook) =====
        with patch('schools_orders.tasks.send_school_order_email') as mock_email_2:
            mock_email_2.return_value = None

            response_2 = self.client.post(
                reverse('boipa:payment_notification'),
                data=payment_notification_data
            )

            # Should still return 200 but not process again
            self.assertEqual(response_2.status_code, 200)
            print("✓ Duplicate notification handled (idempotent)")

        # Verify only ONE enrollment exists (no duplicates)
        enrollment_count = ScoEnrollment.objects.filter(
            swimling=self.swimling,
            lesson=self.sco_lesson,
            term=self.sco_term
        ).count()
        self.assertEqual(enrollment_count, 1)
        print("✓ Only one enrollment exists (no duplicates)")

        # Verify only ONE notification record exists
        notification_count = SchoolOrderPaymentNotification.objects.filter(order=order).count()
        self.assertEqual(notification_count, 1)
        print("✓ Only one notification record exists")

        print("\n" + "="*60)
        print("✅ SCHOOL ORDER PAYMENT FLOW WITH ENROLLMENT TEST PASSED")
        print("="*60)
        print(f"Order ID: {order.id}")
        print(f"School: {order.school.name}")
        print(f"Product: {order.items.first().product.name}")
        print(f"Amount: €{order.amount}")
        print(f"Paid: {order.paid}")
        print(f"Transaction ID: {order.txId}")
        print(f"Enrollment ID: {enrollment.id}")
        print(f"Enrollment: {enrollment.swimling} → {enrollment.lesson.category.name}")
        print("="*60)

    def test_school_order_failed_payment_no_enrollment(self):
        """
        Test that failed payment does NOT create enrollment
        """
        # Create order
        order = Order.objects.create(
            user=self.user,
            school=self.school,
            amount=Decimal('150.00'),
            paid=False
        )

        OrderItem.objects.create(
            order=order,
            product=self.sco_lesson,
            price=self.sco_lesson.price,
            quantity=1,
            swimling=self.swimling,
            term=self.sco_term
        )

        # Simulate failed payment notification
        merchant_tx_id = f"school_{order.id}_{int(time_module.time())}"
        failed_payment_data = {
            'merchantTxId': merchant_tx_id,
            'txId': 'BOIPA_TX_FAILED_99999',
            'result': 'failure',
            'status': 'DECLINED',
            'amount': '150.00',
            'currency': 'EUR',
            'country': 'IE',
            'errorMessage': 'Payment declined by bank',
        }

        with patch('schools_orders.tasks.send_school_order_email') as mock_email:
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
        notification = SchoolOrderPaymentNotification.objects.filter(order=order).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.status, 'DECLINED')
        self.assertEqual(notification.errorMessage, 'Payment declined by bank')
        print(f"✓ Failed payment notification recorded: {notification.id}")

        # **KEY TEST:** Verify NO enrollment created for failed payment
        enrollment_count = ScoEnrollment.objects.filter(
            swimling=self.swimling,
            lesson=self.sco_lesson,
            term=self.sco_term
        ).count()
        self.assertEqual(enrollment_count, 0)
        print("✓ NO enrollment created for failed payment")

        print("\n" + "="*60)
        print("✅ FAILED PAYMENT NO ENROLLMENT TEST PASSED")
        print("="*60)

    def test_school_order_multiple_students(self):
        """
        Test order with multiple students (multiple enrollments)
        Common scenario: School books multiple children for the same lesson
        """
        # Create second swimling (another student)
        student_2 = Swimling.objects.create(
            guardian=self.user,
            first_name='Another',
            last_name='Student',
            dob=date(2016, 3, 20),
            sco_role_num='STU002'
        )

        # Create order with 2 students
        order = Order.objects.create(
            user=self.user,
            school=self.school,
            amount=Decimal('300.00'),  # 2 x €150
            paid=False
        )

        # Create order items for both students
        OrderItem.objects.create(
            order=order,
            product=self.sco_lesson,
            price=self.sco_lesson.price,
            quantity=1,
            swimling=self.swimling,
            term=self.sco_term
        )

        OrderItem.objects.create(
            order=order,
            product=self.sco_lesson,
            price=self.sco_lesson.price,
            quantity=1,
            swimling=student_2,
            term=self.sco_term
        )

        # Verify order items
        self.assertEqual(order.items.count(), 2)
        print(f"✓ Multi-student order created: {order.items.count()} students, €{order.amount}")

        # Simulate successful payment
        merchant_tx_id = f"school_{order.id}_{int(time_module.time())}"
        payment_data = {
            'merchantTxId': merchant_tx_id,
            'txId': 'BOIPA_TX_MULTI_55555',
            'result': 'success',
            'status': 'CAPTURED',
            'amount': '300.00',
            'currency': 'EUR',
            'country': 'IE',
        }

        with patch('schools_orders.tasks.send_school_order_email'):
            response = self.client.post(
                reverse('boipa:payment_notification'),
                data=payment_data
            )
            self.assertEqual(response.status_code, 200)

        # Verify payment processed
        order.refresh_from_db()
        self.assertTrue(order.paid)
        self.assertEqual(order.txId, 'BOIPA_TX_MULTI_55555')
        print(f"✓ Multi-student order paid: Order {order.id}")

        # **KEY TEST:** Verify BOTH enrollments created
        enrollments = ScoEnrollment.objects.filter(
            lesson=self.sco_lesson,
            term=self.sco_term,
            order=order
        ).order_by('swimling__first_name')

        self.assertEqual(enrollments.count(), 2)
        print(f"✓ Created {enrollments.count()} enrollments for {order.items.count()} students")

        # Verify first student enrolled
        student1_enrollment = enrollments.filter(swimling=self.swimling).first()
        self.assertIsNotNone(student1_enrollment)
        self.assertEqual(student1_enrollment.swimling, self.swimling)
        print(f"  - Student 1 enrolled: {student1_enrollment.swimling.first_name} (Roll: {student1_enrollment.swimling.sco_role_num})")

        # Verify second student enrolled
        student2_enrollment = enrollments.filter(swimling=student_2).first()
        self.assertIsNotNone(student2_enrollment)
        self.assertEqual(student2_enrollment.swimling, student_2)
        print(f"  - Student 2 enrolled: {student2_enrollment.swimling.first_name} (Roll: {student2_enrollment.swimling.sco_role_num})")

        print("\n" + "="*60)
        print("✅ MULTI-STUDENT ENROLLMENT TEST PASSED")
        print("="*60)

    def test_school_order_multiple_lessons_same_student(self):
        """
        Test order with one student in multiple lessons
        Example: Student enrolled in both Water Safety and Swim Skills
        """
        # Create second lesson category and lesson
        category_2 = ScoCategory.objects.create(
            program=self.program,
            name='Swim Skills Level 1',
            slug='swim-skills-1'
        )

        sco_lesson_2 = ScoLessons.objects.create(
            category=category_2,
            school=self.school,
            day_of_week=4,  # Friday
            start_time=time(14, 0),
            end_time=time(15, 0),
            num_places=25,
            num_weeks=12,
            price=Decimal('150.00'),
            active=True
        )

        # Create order with 2 lessons for same student
        order = Order.objects.create(
            user=self.user,
            school=self.school,
            amount=Decimal('300.00'),  # 2 x €150
            paid=False
        )

        # Create order items for both lessons
        OrderItem.objects.create(
            order=order,
            product=self.sco_lesson,  # Wednesday Water Safety
            price=self.sco_lesson.price,
            quantity=1,
            swimling=self.swimling,
            term=self.sco_term
        )

        OrderItem.objects.create(
            order=order,
            product=sco_lesson_2,  # Friday Swim Skills
            price=sco_lesson_2.price,
            quantity=1,
            swimling=self.swimling,
            term=self.sco_term
        )

        print(f"✓ Multi-lesson order created: {order.items.count()} lessons for 1 student, €{order.amount}")

        # Simulate successful payment
        merchant_tx_id = f"school_{order.id}_{int(time_module.time())}"
        payment_data = {
            'merchantTxId': merchant_tx_id,
            'txId': 'BOIPA_TX_MULTILESSON_77777',
            'result': 'success',
            'status': 'CAPTURED',
            'amount': '300.00',
            'currency': 'EUR',
            'country': 'IE',
        }

        with patch('schools_orders.tasks.send_school_order_email'):
            response = self.client.post(
                reverse('boipa:payment_notification'),
                data=payment_data
            )
            self.assertEqual(response.status_code, 200)

        # Verify payment processed
        order.refresh_from_db()
        self.assertTrue(order.paid)
        print(f"✓ Multi-lesson order paid: Order {order.id}")

        # **KEY TEST:** Verify enrollments for BOTH lessons
        enrollments = ScoEnrollment.objects.filter(
            swimling=self.swimling,
            term=self.sco_term,
            order=order
        ).order_by('lesson__day_of_week')

        self.assertEqual(enrollments.count(), 2)
        print(f"✓ Created {enrollments.count()} enrollments for {order.items.count()} lessons")

        # Verify Wednesday lesson enrollment
        wed_enrollment = enrollments.filter(lesson=self.sco_lesson).first()
        self.assertIsNotNone(wed_enrollment)
        self.assertEqual(wed_enrollment.lesson.day_of_week, 2)  # Wednesday
        print(f"  - Enrolled in Wednesday lesson: {wed_enrollment.lesson.name}")

        # Verify Friday lesson enrollment
        fri_enrollment = enrollments.filter(lesson=sco_lesson_2).first()
        self.assertIsNotNone(fri_enrollment)
        self.assertEqual(fri_enrollment.lesson.day_of_week, 4)  # Friday
        print(f"  - Enrolled in Friday lesson: {fri_enrollment.lesson.name}")

        print("\n" + "="*60)
        print("✅ MULTI-LESSON ENROLLMENT TEST PASSED")
        print("="*60)