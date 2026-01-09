"""
Management command to test BOIPA API connection and credentials.

Usage:
    python manage.py test_boipa_connection
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from boipa.payment_functions import get_boipa_access_token, create_hpp_payment_link
from decimal import Decimal


class Command(BaseCommand):
    help = 'Test BOIPA API connection and credentials'

    def handle(self, *args, **options):
        self.stdout.write('='*60)
        self.stdout.write(self.style.WARNING('BOIPA Connection Test'))
        self.stdout.write('='*60 + '\n')

        # Step 1: Check environment variables
        self.stdout.write(self.style.WARNING('1. Checking Environment Variables:\n'))

        required_vars = [
            'BOIPA_APP_ID',
            'BOIPA_APP_KEY',
            'BOIPA_ACCOUNT_NAME',
            'BOIPA_API_BASE_URL',
            'BOIPA_ACCESS_TOKEN_URL',
            'BOIPA_HPP_LINKS_URL',
            'BOIPA_API_VERSION',
        ]

        all_vars_present = True
        for var in required_vars:
            value = getattr(settings, var, None)
            if value and value != 'DEPRECATED':
                # Mask sensitive values
                if 'KEY' in var or 'SECRET' in var:
                    display_value = value[:8] + '...' if len(value) > 8 else '***'
                else:
                    display_value = value
                self.stdout.write(f"   ✅ {var}: {display_value}")
            else:
                self.stdout.write(self.style.ERROR(f"   ❌ {var}: NOT SET or DEPRECATED"))
                all_vars_present = False

        if not all_vars_present:
            self.stdout.write(self.style.ERROR('\n❌ Missing required environment variables!'))
            self.stdout.write('\nPlease ensure your .env file has:')
            self.stdout.write('   BOIPA_APP_ID=your_app_id')
            self.stdout.write('   BOIPA_APP_KEY=your_app_key')
            self.stdout.write('   BOIPA_ACCOUNT_NAME=transaction_processing')
            self.stdout.write('   BOIPA_API_BASE_URL=https://apis.boipagateway.com')
            self.stdout.write('   BOIPA_ACCESS_TOKEN_URL=https://apis.boipagateway.com/ucp/accesstoken')
            self.stdout.write('   BOIPA_HPP_LINKS_URL=https://apis.boipagateway.com/ucp/links')
            self.stdout.write('   BOIPA_API_VERSION=2021-03-22\n')
            return

        # Step 2: Test access token generation
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('2. Testing Access Token Generation:\n'))

        try:
            token_data = get_boipa_access_token()

            if token_data and 'token' in token_data:
                self.stdout.write(self.style.SUCCESS('   ✅ Access token obtained successfully!'))
                self.stdout.write(f"   Token: {token_data['token'][:20]}...")
                self.stdout.write(f"   Expires in: {token_data.get('expires_in', 'N/A')} seconds")
                self.stdout.write(f"   Accounts: {token_data.get('accounts', 'N/A')}")
            else:
                self.stdout.write(self.style.ERROR('   ❌ Failed to obtain access token'))
                self.stdout.write('   Check the logs for details')
                return

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error: {str(e)}'))
            return

        # Step 3: Test HPP link creation (with fake request)
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('3. Testing HPP Link Creation:\n'))

        try:
            # Create a mock request object
            class MockRequest:
                def __init__(self):
                    self.META = {}
                def build_absolute_uri(self, path):
                    return settings.NGROK + path

            mock_request = MockRequest()
            test_amount = Decimal('10.00')
            test_order_ref = 'test_order_999'

            self.stdout.write(f'   Creating test HPP link for €{test_amount}...')

            link_data = create_hpp_payment_link(
                mock_request,
                test_order_ref,
                test_amount,
                payer_info={'name': 'Test User', 'email': 'test@example.com'}
            )

            if link_data and 'url' in link_data:
                self.stdout.write(self.style.SUCCESS('   ✅ HPP link created successfully!'))
                self.stdout.write(f"   Link ID: {link_data.get('id', 'N/A')}")
                self.stdout.write(f"   URL: {link_data['url'][:60]}...")
                self.stdout.write(f"   Status: {link_data.get('status', 'N/A')}")
            else:
                self.stdout.write(self.style.ERROR('   ❌ Failed to create HPP link'))
                self.stdout.write('   Check the logs for details')
                return

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   ❌ Error: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())
            return

        # Step 4: Check callback URLs
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('4. Checking Callback URLs:\n'))

        base_url = settings.NGROK
        if base_url.endswith("tcsp.ie"):
            base_url = "https://www.tcsp.ie"

        from django.urls import reverse
        callback_urls = {
            'Return URL': base_url + reverse('boipa:payment_response'),
            'Notification URL': base_url + reverse('boipa:payment_notification'),
            'Cancel URL': base_url + reverse('home'),
        }

        for name, url in callback_urls.items():
            self.stdout.write(f'   {name}: {url}')

        # Final summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✅ All BOIPA connection tests passed!'))
        self.stdout.write('='*60)
        self.stdout.write('\nYour BOIPA integration is configured correctly.')
        self.stdout.write('You should be able to process payments.\n')