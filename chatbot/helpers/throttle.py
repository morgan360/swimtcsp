"""Per-session throttling for the public chatbot endpoints.

Both endpoints are unauthenticated by design — customers use them before they
have an account — but every message spends OpenAI credits, so an unthrottled
caller can run up a bill at will.
"""
from django.conf import settings
from django.core.cache import cache

WINDOW_SECONDS = 60 * 60

TOO_MANY_MESSAGES = (
    "You've sent a lot of messages in a short time. Please wait a little while "
    "before asking again, or contact reception if it's urgent."
)


def _bucket_key(request):
    session_key = request.session.session_key or "anonymous"
    return f"chatbot:rate:{session_key}"


def is_rate_limited(request):
    """True once this session has exceeded its hourly message allowance."""
    limit = getattr(settings, "CHATBOT_MAX_MESSAGES_PER_HOUR", 30)
    if limit <= 0:
        return False

    key = _bucket_key(request)
    count = cache.get(key)
    if count is None:
        # First message of the window starts the clock.
        cache.set(key, 1, WINDOW_SECONDS)
        return False

    if count >= limit:
        return True

    try:
        cache.incr(key)
    except ValueError:
        # Expired between the get and the incr; start a new window.
        cache.set(key, 1, WINDOW_SECONDS)
    return False
