from django.utils.timezone import now
from datetime import timedelta
from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.sessions.exceptions import SessionInterrupted
import logging

logger = logging.getLogger("boipa")


class SetSessionExpiryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set the session to expire when the browser is closed
        request.session.set_expiry(0)

        # Also, set it to expire in 30 minutes if the browser isn't closed
        # This part sets a hard limit on session duration to 30 minutes
        # from the last modification, regardless of browser closure.
        request.session.set_expiry(1800)

        # If you want to check custom conditions or add more complex logic,
        # you can do so here.

        response = self.get_response(request)

        # Optional: Modify response or request after the view is called

        return response


class CustomErrorPageMiddleware:
    """
    Render custom HTML templates for 401 and 503 responses.
    Keeps JSON and other non-HTML responses untouched.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only handle standard, non-streaming HTML responses
        content_type = response.headers.get('Content-Type', '') if hasattr(response, 'headers') else response.get('Content-Type', '')
        is_html = content_type.startswith('text/html') or content_type == ''  # some views may omit

        if getattr(response, 'streaming', False):
            return response

        # Avoid overriding admin login redirect (302) or JSON/API
        if not is_html:
            return response

        if response.status_code == 401:
            return render(request, '401.html', status=401)

        if response.status_code == 503:
            # Add a Retry-After header if not present
            rendered = render(request, '503.html', status=503)
            if 'Retry-After' not in rendered:
                rendered['Retry-After'] = '120'
            return rendered

        return response


class PaymentGatewaySessionMiddleware:
    """
    Handle SessionInterrupted errors from external payment gateway callbacks.

    When BOIPA posts payment responses from their domain, there's no session context.
    This causes Django's session middleware to raise SessionInterrupted when trying
    to save a session that doesn't exist. This middleware catches that exception
    and allows the response to proceed normally.

    This must be placed AFTER SessionMiddleware in MIDDLEWARE settings.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except SessionInterrupted:
            # Check if this is a payment gateway callback endpoint
            if '/boipa/payment-' in request.path or '/boipa/payment_' in request.path:
                logger.warning(
                    f"SessionInterrupted on payment callback: {request.path} - "
                    "This is expected for external gateway callbacks from BOIPA"
                )
                # Return a simple HTML response
                # The payment was already processed before the session error occurred
                html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Payment Processed</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f9ff; }
        .container { background: white; padding: 40px; border-radius: 10px; max-width: 500px; margin: 0 auto; }
        h1 { color: #16a34a; }
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Payment Processed</h1>
        <p>Your payment has been received and is being processed.</p>
        <p>You may close this window.</p>
    </div>
</body>
</html>
"""
                return HttpResponse(html, status=200)
            # Re-raise if it's not a payment callback
            raise
