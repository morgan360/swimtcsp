"""Per-caller throttling for the public chatbot endpoints.

Both endpoints are unauthenticated by design — customers use them before they
have an account — but every message spends OpenAI credits, so an unthrottled
caller can run up a bill at will.

Two buckets are counted, and a caller is refused when *either* is full:

    session   the generous one, and the only one a real customer will ever meet
    IP        the backstop that actually costs an abuser something

Keying on the session alone — which is all this used to do — was no defence at
all. The views create a session for any caller arriving without one, so a client
that simply discards cookies got a brand-new, empty bucket on every single
request. CSRF was no obstacle either: the token is cookie-based, so any
self-generated cookie/header pair passes. Rotating sessions is free; rotating
source addresses is not, which is why the IP bucket is the one doing the work.

Both counters live in the shared cache backend. That matters as much as the
keys: under the per-process default they were per worker, so the effective limit
was whatever was configured times the number of workers. See CACHES in
base_settings.
"""
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 60 * 60

TOO_MANY_MESSAGES = (
    "You've sent a lot of messages in a short time. Please wait a little while "
    "before asking again, or contact reception if it's urgent."
)


def client_ip(request):
    """The caller's address, taken only from sources a client cannot forge.

    Behind a trusted proxy the address comes from the header that proxy writes
    (CHATBOT_CLIENT_IP_HEADER); with no proxy configured it comes from
    REMOTE_ADDR. A client-supplied header is never consulted — trusting one
    would hand back exactly the bypass this module exists to close.
    """
    header = getattr(settings, "CHATBOT_CLIENT_IP_HEADER", "HTTP_X_REAL_IP")
    if header:
        value = (request.META.get(header) or "").strip()
        if value:
            return value
    return (request.META.get("REMOTE_ADDR") or "").strip()


def _consume(key, limit):
    """Count one message against `key`. True once `limit` is used up.

    The window is fixed, not sliding: the first message starts the clock and the
    TTL is never extended, so a blocked caller is always let back in within an
    hour rather than being locked out for as long as they keep trying.
    """
    if limit <= 0:  # 0 or negative disables this bucket entirely.
        return False

    count = cache.get(key)
    if count is None:
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


def is_rate_limited(request):
    """True once this caller has exceeded either hourly allowance."""
    session_key = request.session.session_key or "anonymous"
    ip = client_ip(request)

    # Evaluated eagerly, both of them: short-circuiting on the session bucket
    # would leave the IP bucket under-counted for exactly the caller it is meant
    # to catch.
    session_blocked = _consume(
        f"chatbot:rate:session:{session_key}",
        getattr(settings, "CHATBOT_MAX_MESSAGES_PER_HOUR", 30),
    )
    ip_blocked = _consume(
        # No IP resolved at all (unlikely — it means neither the proxy header
        # nor REMOTE_ADDR was set): everyone in that position shares one bucket,
        # which is the conservative way round.
        f"chatbot:rate:ip:{ip or 'unknown'}",
        getattr(settings, "CHATBOT_MAX_MESSAGES_PER_HOUR_PER_IP", 120),
    )

    if ip_blocked:
        # The session bucket filling up is ordinary; the IP bucket filling up
        # means someone is cycling sessions, and that is worth being able to see.
        logger.warning("Chatbot per-IP rate limit reached for %s", ip or "unknown")

    return session_blocked or ip_blocked