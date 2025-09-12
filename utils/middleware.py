from django.utils.timezone import now
from datetime import timedelta
from django.shortcuts import render
from django.http import HttpResponse


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
