#!/usr/bin/env python
"""
Test BOIPA Sandbox API Integration
Tests the new OAuth2-based BOIPA API with sandbox credentials
"""

import os
import sys
import django
from pathlib import Path

# Setup Django environment
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.local_settings')
django.setup()

from django.conf import settings
from boipa.payment_functions import get_boipa_access_token, create_hpp_payment_link
from decimal import Decimal
import json


def test_access_token():
    """Test 1: Generate OAuth2 access token"""
    print("\n" + "="*60)
    print("TEST 1: BOIPA Access Token Generation")
    print("="*60)

    print(f"\n📋 Configuration:")
    print(f"   APP_ID: {settings.BOIPA_APP_ID}")
    print(f"   APP_KEY: {settings.BOIPA_APP_KEY[:4]}...{settings.BOIPA_APP_KEY[-4:]}")
    print(f"   API URL: {settings.BOIPA_ACCESS_TOKEN_URL}")
    print(f"   API Version: {settings.BOIPA_API_VERSION}")

    print(f"\n🔄 Requesting access token...")
    token_data = get_boipa_access_token()

    if token_data:
        print(f"\n✅ SUCCESS! Access token obtained")
        print(f"   Token: {token_data.get('token', '')[:20]}...{token_data.get('token', '')[-10:]}")
        print(f"   Expires in: {token_data.get('expires_in')} seconds")
        print(f"   Token type: {token_data.get('type', 'N/A')}")

        if 'accounts' in token_data:
            print(f"   Accounts available: {len(token_data['accounts'])}")
            for account in token_data.get('accounts', []):
                print(f"      - {account.get('name', 'N/A')}")

        return token_data
    else:
        print(f"\n❌ FAILED to obtain access token")
        print(f"   Check logs/boipa.log for details")
        return None


def test_hpp_link_creation():
    """Test 2: Create a Hosted Payment Page link"""
    print("\n" + "="*60)
    print("TEST 2: Create HPP Payment Link")
    print("="*60)

    # Create a mock request object
    class MockRequest:
        user = type('obj', (object,), {
            'is_authenticated': True,
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@tcsp.ie'
        })()
        META = {'REMOTE_ADDR': '127.0.0.1'}

    request = MockRequest()
    order_ref = f"test_sandbox_{int(__import__('time').time())}"
    total_price = Decimal("25.50")

    payer_info = {
        'name': 'Test User',
        'email': 'test@tcsp.ie',
        'billing_address': {
            'line_1': '123 Test Street',
            'city': 'Dublin',
            'postal_code': 'D02 X285',
            'country': 'IE'
        }
    }

    print(f"\n📋 Payment Details:")
    print(f"   Order Reference: {order_ref}")
    print(f"   Amount: €{total_price}")
    print(f"   Payer: {payer_info['name']} ({payer_info['email']})")
    print(f"   Account: {settings.BOIPA_ACCOUNT_NAME}")

    print(f"\n🔄 Creating HPP link...")
    link_data = create_hpp_payment_link(request, order_ref, total_price, payer_info)

    if link_data and 'url' in link_data:
        print(f"\n✅ SUCCESS! HPP link created")
        print(f"   Link ID: {link_data.get('id')}")
        print(f"   Payment URL: {link_data.get('url')}")
        print(f"   Status: {link_data.get('status')}")
        print(f"\n🌐 You can test this link in your browser:")
        print(f"   {link_data.get('url')}")
        print(f"\n💳 Use test cards from docs/BOIPA_TEST_CARDS.md")

        return link_data
    else:
        print(f"\n❌ FAILED to create HPP link")
        print(f"   Check logs/boipa.log for details")
        return None


def main():
    """Run all sandbox tests"""
    print("\n" + "="*60)
    print("🧪 BOIPA SANDBOX API TEST SUITE")
    print("="*60)
    print(f"\nEnvironment: SANDBOX")
    print(f"Merchant ID: {settings.BOIPA_MERCHANT_ID}")
    print(f"Account Name: {settings.BOIPA_ACCOUNT_NAME}")

    # Test 1: Access Token
    token_result = test_access_token()
    if not token_result:
        print("\n⚠️  Cannot proceed with HPP test without valid access token")
        return False

    # Test 2: HPP Link Creation
    hpp_result = test_hpp_link_creation()

    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"✅ Access Token: {'PASS' if token_result else 'FAIL'}")
    print(f"✅ HPP Link Creation: {'PASS' if hpp_result else 'FAIL'}")

    if token_result and hpp_result:
        print("\n🎉 All tests passed! Sandbox integration is working.")
        print("\n📝 Next Steps:")
        print("   1. Open the HPP URL in your browser")
        print("   2. Use test card: 4263970000005262 (CVV: 123, Exp: 12/25)")
        print("   3. Check webhook receives notification at /boipa/payment-notification/")
        print("   4. Review logs/boipa.log for full request/response details")
        return True
    else:
        print("\n❌ Some tests failed. Check logs/boipa.log for details")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)