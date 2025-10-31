"""
BOIPA Sandbox Test Card Details

These test card numbers are for use with BOIPA's sandbox/UAT environment.
Source: BOIPA-Test-Cases.pdf (3DS 2.1 compliant)

IMPORTANT: These cards only work in BOIPA sandbox environment:
- Token URL: https://apiuat.test.boipapaymentgateway.com/token
- HPP Form: https://cashierui-apiuat.test.boipapaymentgateway.com/
- Merchant ID: 100121 (sandbox)

The outcome of each test scenario is triggered by the card details used.
Different cards test different 3D Secure flows and authentication scenarios.
"""


class BOIPATestCards:
    """
    BOIPA Sandbox test card numbers for different 3DS v2.1 scenarios.

    Usage in tests:
        card = BOIPATestCards.VISA_FRICTIONLESS_SUCCESS
        print(f"Testing with: {card['description']}")
        # Card number: {card['number']}
        # CVV: {card['cvv']}
    """

    # ============================================================================
    # TEST CASE 1: Challenge Flow - Successful Authentication (3DS v2.1)
    # ============================================================================
    # Customer is presented with 3DS challenge (e.g., enter PIN on bank's page)
    # Customer successfully completes the challenge
    # Transaction proceeds to payment authorization

    VISA_CHALLENGE_SUCCESS = {
        'number': '4111111111111111',
        'cvv': '123',
        'pin': '1234',  # Use this PIN in 3DS challenge to succeed
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Visa - Challenge flow successful',
        'test_case_id': 1,
        '3ds_version': '2.1',
        'flow_type': 'challenge',
        'expected_result': 'Transaction completes successfully'
    }

    MASTERCARD_CHALLENGE_SUCCESS = {
        'number': '5454545454545454',
        'cvv': '123',
        'pin': '1234',  # Use this PIN in 3DS challenge to succeed
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Mastercard - Challenge flow successful',
        'test_case_id': 1,
        '3ds_version': '2.1',
        'flow_type': 'challenge',
        'expected_result': 'Transaction completes successfully'
    }

    # ============================================================================
    # TEST CASE 2: Frictionless Flow - Successful Authentication (3DS v2.1)
    # ============================================================================
    # No challenge presented to customer (frictionless)
    # Customer is automatically authenticated by their bank
    # Transaction proceeds directly to payment authorization
    # This is the ideal user experience - no friction

    VISA_FRICTIONLESS_SUCCESS = {
        'number': '4539797605519795',
        'cvv': '123',
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Visa - Frictionless flow successful',
        'test_case_id': 2,
        '3ds_version': '2.1',
        'flow_type': 'frictionless',
        'expected_result': 'Transaction goes through to payment authorization'
    }

    MASTERCARD_FRICTIONLESS_SUCCESS = {
        'number': '5307808167635130',
        'cvv': '123',
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Mastercard - Frictionless flow successful',
        'test_case_id': 2,
        '3ds_version': '2.1',
        'flow_type': 'frictionless',
        'expected_result': 'Transaction goes through to payment authorization'
    }

    # ============================================================================
    # TEST CASE 3: Out of Scope Flow (3DS v2.1)
    # ============================================================================
    # For MOTO (Mail Order/Telephone Order) or Merchant Initiated Transactions
    # Transaction accepted as authenticated without cardholder challenge

    VISA_OUT_OF_SCOPE = {
        'number': '4000000000000002',
        'cvv': '123',
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Visa - Out of scope (MOTO)',
        'test_case_id': 3,
        '3ds_version': '2.1',
        'flow_type': 'out_of_scope',
        'expected_result': 'Transaction goes through to payment authorization'
    }

    MASTERCARD_OUT_OF_SCOPE = {
        'number': '5200000000000007',
        'cvv': '123',
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Mastercard - Out of scope (MOTO)',
        'test_case_id': 3,
        '3ds_version': '2.1',
        'flow_type': 'out_of_scope',
        'expected_result': 'Transaction goes through to payment authorization'
    }

    # ============================================================================
    # TEST CASE 4: 3DS v1 Only (Legacy)
    # ============================================================================
    # Card only supports old 3DS version 1
    # Goes through 3DS v1 challenge flow instead of v2

    VISA_3DS_V1_ONLY = {
        'number': '4000000000000002',
        'cvv': '123',
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Visa - 3DS v1 only',
        'test_case_id': 4,
        '3ds_version': '1.0',
        'flow_type': 'challenge',
        'expected_result': 'Transaction is 3DSv1 version V1.0'
    }

    MASTERCARD_3DS_V1_ONLY = {
        'number': '5200000000000007',
        'cvv': '123',
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Mastercard - 3DS v1 only',
        'test_case_id': 4,
        '3ds_version': '1.0',
        'flow_type': 'challenge',
        'expected_result': 'Transaction is 3DSv1 version V1.0'
    }

    # ============================================================================
    # TEST CASE 5: Frictionless Flow - Authentication REJECTED (3DS v2.1)
    # ============================================================================
    # Transaction goes frictionless (no customer challenge)
    # BUT authentication is rejected by the bank
    # Payment does NOT proceed - transaction fails
    # Use this to test declined payment scenarios

    VISA_FRICTIONLESS_REJECTED = {
        'number': '4923842962410313',
        'cvv': '123',
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Visa - Frictionless authentication rejected',
        'test_case_id': 5,
        '3ds_version': '2.1',
        'flow_type': 'frictionless',
        'expected_result': 'Authentication rejection'
    }

    MASTERCARD_FRICTIONLESS_REJECTED = {
        'number': '5498925716675612',
        'cvv': '123',
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Mastercard - Frictionless authentication rejected',
        'test_case_id': 5,
        '3ds_version': '2.1',
        'flow_type': 'frictionless',
        'expected_result': 'Authentication rejection'
    }

    # ============================================================================
    # TEST CASE 6: Challenge Flow - Customer Cancels (3DS v2.1)
    # ============================================================================
    # Customer is presented with 3DS challenge
    # Customer cancels before completing the challenge
    # Transaction is cancelled - payment does NOT proceed
    # NOTE: To simulate this, use the same card as CHALLENGE_SUCCESS
    #       but cancel the 3DS challenge dialog when it appears

    VISA_CHALLENGE_CANCELLED = {
        'number': '4111111111111111',  # Same as CHALLENGE_SUCCESS
        'cvv': '123',
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Visa - Challenge flow cancelled by user',
        'test_case_id': 6,
        '3ds_version': '2.1',
        'flow_type': 'challenge',
        'expected_result': 'Transaction is Cancelled',
        'note': 'User must manually cancel the 3DS challenge dialog'
    }

    MASTERCARD_CHALLENGE_CANCELLED = {
        'number': '5454545454545454',  # Same as CHALLENGE_SUCCESS
        'cvv': '123',
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Mastercard - Challenge flow cancelled by user',
        'test_case_id': 6,
        '3ds_version': '2.1',
        'flow_type': 'challenge',
        'expected_result': 'Transaction is Cancelled',
        'note': 'User must manually cancel the 3DS challenge dialog'
    }

    # ============================================================================
    # TEST CASE 7: Challenge Flow - Authentication FAILED (3DS v2.1)
    # ============================================================================
    # Customer is presented with 3DS challenge
    # Customer enters WRONG PIN (1111 instead of 1234)
    # Authentication fails - payment does NOT proceed
    # Use this to test failed authentication scenarios

    VISA_CHALLENGE_FAILED = {
        'number': '4111111111111111',  # Same card as CHALLENGE_SUCCESS
        'cvv': '123',
        'pin': '1111',  # WRONG PIN - use this to fail authentication
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Visa - Challenge authentication failed (wrong PIN)',
        'test_case_id': 7,
        '3ds_version': '2.1',
        'flow_type': 'challenge',
        'expected_result': 'Transaction fails due to authentication failure',
        'note': 'Enter PIN 1111 (not 1234) to trigger failure'
    }

    MASTERCARD_CHALLENGE_FAILED = {
        'number': '5454545454545454',  # Same card as CHALLENGE_SUCCESS
        'cvv': '123',
        'pin': '1111',  # WRONG PIN - use this to fail authentication
        'expiry_month': '12',
        'expiry_year': '2025',
        'description': 'Mastercard - Challenge authentication failed (wrong PIN)',
        'test_case_id': 7,
        '3ds_version': '2.1',
        'flow_type': 'challenge',
        'expected_result': 'Transaction fails due to authentication failure',
        'note': 'Enter PIN 1111 (not 1234) to trigger failure'
    }

    # ============================================================================
    # Helper Methods
    # ============================================================================

    @classmethod
    def get_success_cards(cls):
        """Get all cards that should result in successful payment"""
        return [
            cls.VISA_CHALLENGE_SUCCESS,
            cls.MASTERCARD_CHALLENGE_SUCCESS,
            cls.VISA_FRICTIONLESS_SUCCESS,
            cls.MASTERCARD_FRICTIONLESS_SUCCESS,
            cls.VISA_OUT_OF_SCOPE,
            cls.MASTERCARD_OUT_OF_SCOPE,
        ]

    @classmethod
    def get_failure_cards(cls):
        """Get all cards that should result in failed payment"""
        return [
            cls.VISA_FRICTIONLESS_REJECTED,
            cls.MASTERCARD_FRICTIONLESS_REJECTED,
            cls.VISA_CHALLENGE_FAILED,
            cls.MASTERCARD_CHALLENGE_FAILED,
            cls.VISA_CHALLENGE_CANCELLED,
            cls.MASTERCARD_CHALLENGE_CANCELLED,
        ]

    @classmethod
    def get_card_by_test_case(cls, test_case_id, card_type='visa'):
        """
        Get test card for a specific test case ID

        Args:
            test_case_id: Test case number (1-7)
            card_type: 'visa' or 'mastercard'

        Returns:
            dict: Card details
        """
        cards = {
            1: cls.VISA_CHALLENGE_SUCCESS if card_type == 'visa' else cls.MASTERCARD_CHALLENGE_SUCCESS,
            2: cls.VISA_FRICTIONLESS_SUCCESS if card_type == 'visa' else cls.MASTERCARD_FRICTIONLESS_SUCCESS,
            3: cls.VISA_OUT_OF_SCOPE if card_type == 'visa' else cls.MASTERCARD_OUT_OF_SCOPE,
            4: cls.VISA_3DS_V1_ONLY if card_type == 'visa' else cls.MASTERCARD_3DS_V1_ONLY,
            5: cls.VISA_FRICTIONLESS_REJECTED if card_type == 'visa' else cls.MASTERCARD_FRICTIONLESS_REJECTED,
            6: cls.VISA_CHALLENGE_CANCELLED if card_type == 'visa' else cls.MASTERCARD_CHALLENGE_CANCELLED,
            7: cls.VISA_CHALLENGE_FAILED if card_type == 'visa' else cls.MASTERCARD_CHALLENGE_FAILED,
        }
        return cards.get(test_case_id)


# Convenience aliases for common test scenarios
BOIPA_SUCCESS_CARD = BOIPATestCards.VISA_FRICTIONLESS_SUCCESS  # Most common success scenario
BOIPA_FAILURE_CARD = BOIPATestCards.VISA_FRICTIONLESS_REJECTED  # Most common failure scenario
BOIPA_CHALLENGE_CARD = BOIPATestCards.VISA_CHALLENGE_SUCCESS  # For testing 3DS challenge flow