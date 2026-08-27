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

        # ===== STEP 2: Build the merchantTxId the checkout would have sent =====
        # No BOIPA call to mock here: this test posts the webhook directly rather
        # than going through checkout, so it only needs the reference format.
        merchant_tx_id = f"lesson_{order.id}_{int(time_module.time())}"
        print(f"✓ merchantTxId: {merchant_tx_id}")

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

class OrderDiscountDisplayTests(TestCase):
    """Discounts shown to the customer come from CouponRedemption rows.

    Order.discount_amount was never a real database field — a stray trailing
    comma in models.py makes it a tuple, and migration 0009 dropped the column —
    so assigning to it silently did nothing and the confirmation page and
    booking card rendered a blank or a tuple repr where a figure belonged.
    """

    def setUp(self):
        from coupons.models import Coupon, CouponRedemption
        from django.contrib.contenttypes.models import ContentType

        self.user = User.objects.create_user(
            email="discount@example.com", password="pw12345!"
        )
        self.order = Order.objects.create(user=self.user, amount=Decimal("59.50"), paid=True)
        self.ct = ContentType.objects.get_for_model(Order)
        self.Coupon, self.CouponRedemption = Coupon, CouponRedemption

    def _redeem(self, code, amount):
        now = timezone.now()
        coupon = self.Coupon.objects.create(
            code=code, discount_type="fixed", discount_value=Decimal(amount),
            balance_remaining=Decimal(amount),
            valid_from=now - timedelta(days=1), valid_to=now + timedelta(days=30),
        )
        return self.CouponRedemption.objects.create(
            coupon=coupon, redeemed_amount=Decimal(amount),
            content_type=self.ct, object_id=self.order.id,
        )

    def test_total_discount_sums_every_redemption(self):
        self._redeem("TEST-A", "20.50")
        self._redeem("TEST-B", "10.00")
        self.assertEqual(self.order.total_discount, Decimal("30.50"))

    def test_total_discount_is_zero_without_redemptions(self):
        self.assertEqual(self.order.total_discount, Decimal("0.00"))

    def test_discount_amount_is_still_not_a_real_field(self):
        """Guard: if this ever starts passing as a field, the templates can move back."""
        field_names = [f.name for f in Order._meta.get_fields()]
        self.assertNotIn("discount_amount", field_names)

    def _render(self, template, context):
        import html as html_mod
        import re
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        request = RequestFactory().get("/")
        request.user = self.user
        request.session = {}
        out = render_to_string(template, context, request=request)
        return re.sub(r"\s+", " ", html_mod.unescape(re.sub(r"<[^>]+>", " ", out)))

    def test_booking_card_shows_the_real_discount(self):
        self._redeem("TEST-A", "20.50")
        text = self._render("users/_lesson_booking_card.html", {
            "order": self.order, "status_label": "Paid",
            "status_classes": "", "status_hint": "",
        })
        self.assertIn("TEST-A", text)
        self.assertIn("20.50", text)

    def test_confirmation_page_lists_each_coupon(self):
        self._redeem("TEST-A", "20.50")
        self._redeem("TEST-B", "10.00")
        text = self._render("orders/order/created.html", {"order": self.order})
        self.assertIn("TEST-A", text)
        self.assertIn("TEST-B", text)
        # With more than one coupon the page also shows the combined figure.
        self.assertIn("30.50", text)


class CheckoutCouponFailureTests(TestCase):
    """A coupon that stops validating must not silently cost the customer money.

    Previously payment_process logged the failure and carried on, so the customer
    reached the payment page owing the undiscounted amount with no explanation.
    """

    def setUp(self):
        from coupons.models import Coupon
        from lessons_bookings.models import Term

        self.client = Client()
        self.user = User.objects.create_user(email="checkout@example.com", password="pw12345!")
        self.client.force_login(self.user)

        now = timezone.now()
        today = now.date()
        self.program = Program.objects.create(name="Checkout Prog")
        self.category = Category.objects.create(
            program=self.program, name="Checkout Cat",
            slug="checkout-cat", stage="Stage 1",
        )
        # Booking is open but the term has not started, so the cart charges the
        # full term price. Starting it today would prorate per remaining lesson,
        # which varies with the weekday the suite happens to run on.
        self.term = Term.objects.create(
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=63),
            rebooking_date=today - timedelta(days=7),
            booking_date=today - timedelta(days=5),
            assessment_date=today + timedelta(days=64),
        )
        self.swimling = Swimling.objects.create(
            guardian=self.user, first_name="Kid", last_name="Test",
            dob=date(2016, 1, 1),
        )
        self.product = Product.objects.create(
            category=self.category, day_of_week=0,
            start_time=time(10, 0), end_time=time(10, 45),
            num_places=10, num_weeks=8,
            price=Decimal("100.00"), active=True,
        )
        self.Coupon = Coupon
        self.now = now

    def _make_coupon(self, code, value="20.00", **kwargs):
        opts = dict(
            code=code, discount_type="fixed", discount_value=Decimal(value),
            balance_remaining=Decimal(value),
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=30),
        )
        opts.update(kwargs)
        return self.Coupon.objects.create(**opts)

    def _seed_cart(self, codes):
        """Build the cart through the real Cart API so its shape stays correct."""
        from shopping_cart.cart import Cart

        request = type("R", (), {})()
        request.session = self.client.session
        cart = Cart(request)
        cart.add(product=self.product, type="lesson",
                 swimling_id=self.swimling.id, term=self.term)

        request.session["coupon_codes"] = codes
        request.session.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = request.session.session_key

    def test_expired_coupon_blocks_checkout_instead_of_charging_full_price(self):
        from coupons.models import CouponRedemption

        # Valid when added to the cart, expired by the time they press pay.
        coupon = self._make_coupon("GONE-OFF")
        coupon.valid_to = self.now - timedelta(hours=1)
        coupon.save()
        self._seed_cart(["GONE-OFF"])

        orders_before = Order.objects.count()
        response = self.client.get(reverse("shopping_cart:payment_process"), follow=True)

        # Sent back to the cart, told why, and nothing was created or spent.
        self.assertContains(response, "has not been placed")
        self.assertEqual(Order.objects.count(), orders_before)
        self.assertEqual(CouponRedemption.objects.count(), 0)
        self.assertEqual(self.Coupon.objects.get(code="GONE-OFF").times_used, 0)

    def test_one_bad_coupon_does_not_spend_the_good_one(self):
        """The failure must not leave the first coupon already redeemed."""
        from coupons.models import CouponRedemption

        good = self._make_coupon("GOOD-ONE")
        bad = self._make_coupon("BAD-ONE")
        bad.valid_to = self.now - timedelta(hours=1)
        bad.save()
        self._seed_cart(["GOOD-ONE", "BAD-ONE"])

        self.client.get(reverse("shopping_cart:payment_process"), follow=True)

        self.assertEqual(CouponRedemption.objects.count(), 0)
        good.refresh_from_db()
        self.assertEqual(good.times_used, 0)
        self.assertEqual(good.balance_remaining, Decimal("20.00"))

    def test_valid_coupons_still_check_out_and_discount(self):
        from coupons.models import CouponRedemption

        self._make_coupon("FINE-ONE", "25.00")
        self._seed_cart(["FINE-ONE"])

        self.client.get(reverse("shopping_cart:payment_process"), follow=True)

        order = Order.objects.filter(user=self.user).order_by("-id").first()
        self.assertIsNotNone(order)
        self.assertEqual(order.amount, Decimal("75.00"))
        self.assertEqual(order.total_discount, Decimal("25.00"))
        self.assertEqual(CouponRedemption.objects.count(), 1)

    def test_two_valid_coupons_stack_on_the_order(self):
        """The point of the feature: both come off, and both are recorded."""
        from coupons.models import CouponRedemption

        self._make_coupon("PAIR-A", "25.00")
        self._make_coupon("PAIR-B", "15.00")
        self._seed_cart(["PAIR-A", "PAIR-B"])

        self.client.get(reverse("shopping_cart:payment_process"), follow=True)

        order = Order.objects.filter(user=self.user).order_by("-id").first()
        self.assertIsNotNone(order)
        self.assertEqual(order.amount, Decimal("60.00"))
        self.assertEqual(order.total_discount, Decimal("40.00"))
        self.assertEqual(CouponRedemption.objects.count(), 2)

        # Both are spent, not just the one recorded on the legacy order.coupon.
        for code, value in (("PAIR-A", "25.00"), ("PAIR-B", "15.00")):
            coupon = self.Coupon.objects.get(code=code)
            self.assertEqual(coupon.times_used, 1, code)
            self.assertEqual(coupon.balance_remaining, Decimal("0.00"), code)

    def test_two_coupons_worth_more_than_the_cart_leave_nothing_to_pay(self):
        """A pair over the cart value must land on zero, never a negative charge."""
        self._make_coupon("OVER-A", "80.00")
        self._make_coupon("OVER-B", "50.00")
        self._seed_cart(["OVER-A", "OVER-B"])

        self.client.get(reverse("shopping_cart:payment_process"), follow=True)

        order = Order.objects.filter(user=self.user).order_by("-id").first()
        self.assertIsNotNone(order)
        self.assertEqual(order.amount, Decimal("0.00"))
        self.assertEqual(order.total_discount, Decimal("100.00"))

        # The second coupon only spent what was left, keeping its unused €30.
        self.assertEqual(
            self.Coupon.objects.get(code="OVER-B").balance_remaining, Decimal("30.00")
        )

    def test_confirmation_email_lists_every_coupon(self):
        """Both halves of the email, since a missing figure fails silently."""
        from django.core import mail
        from lessons_orders.tasks import send_lesson_order_email

        self._make_coupon("MAIL-A", "25.00")
        self._make_coupon("MAIL-B", "15.00")
        self._seed_cart(["MAIL-A", "MAIL-B"])
        self.client.get(reverse("shopping_cart:payment_process"), follow=True)
        order = Order.objects.filter(user=self.user).order_by("-id").first()

        mail.outbox = []
        self.assertTrue(send_lesson_order_email(order.id))

        message = mail.outbox[0]
        html = message.alternatives[0][0]
        for body in (message.body, html):
            self.assertIn("MAIL-A", body)
            self.assertIn("MAIL-B", body)
            self.assertIn("25.00", body)
            self.assertIn("15.00", body)
            self.assertIn("60.00", body)   # the total actually charged

    def test_session_coupons_are_cleared_after_checkout(self):
        """Left behind, they would silently discount the customer's next order."""
        self._make_coupon("ONCE-ONLY", "25.00")
        self._seed_cart(["ONCE-ONLY"])

        self.client.get(reverse("shopping_cart:payment_process"), follow=True)

        self.assertFalse(self.client.session.get("coupon_codes"))
