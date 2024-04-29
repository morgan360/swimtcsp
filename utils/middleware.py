from django.utils.timezone import now
from datetime import timedelta


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
