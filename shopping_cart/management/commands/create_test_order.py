from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from lessons.models import Product
from users.models import Swimling
from django.contrib.sessions.backends.db import SessionStore
from decimal import Decimal
import uuid

class Command(BaseCommand):
    help = 'Creates a test user, swimling, and cart session with a lesson product'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        test_email = 'testuser@example.com'
        user, created = User.objects.get_or_create(email=test_email, defaults={
            'first_name': 'Test',
            'last_name': 'User',
        })

        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(f'✅ Created test user: {test_email}')
        else:
            self.stdout.write(f'ℹ️ Found existing test user: {test_email}')

        swimling, _ = Swimling.objects.get_or_create(
            guardian=user,
            first_name='Testling',
            last_name='McSwim',
            dob='2015-01-01'
        )

        # Replace with a valid Product ID from your DB
        product = Product.objects.filter(active=True).first()
        if not product:
            self.stderr.write("❌ No active lesson product found.")
            return

        # Create a cart session manually
        session = SessionStore()
        cart_key = f"lesson_{product.id}_{swimling.id}"
        session['cart'] = {
            cart_key: {
                'product_id': str(product.id),
                'swimling_id': str(swimling.id),
                'price': str(product.price),
                'quantity': 1
            }
        }
        session['cart_type'] = 'lesson'
        session.create()

        self.stdout.write("🛒 Test order created in cart session.")
        self.stdout.write(f"🧪 Use this session key in your test login: {session.session_key}")
