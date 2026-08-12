"""Email notification when the chatbot refuses an abusive message.

The July 2026 incident sat in ChatbotQuery for three weeks before anyone looked.
Detecting abuse without telling anyone only converts it into a row nobody reads,
so the flag and the alert ship together.

Two things this deliberately does *not* do:

Send one email per flagged message. A single session in July produced ten in
four minutes; ten emails would train the recipient to ignore them. One alert per
session per cooldown window is enough to say "look at this session now", and the
admin holds the full transcript.

Break the response. Every failure path returns rather than raising: a refusal
that a customer sees is more important than an alert that an operator sees, and
an SMTP timeout must not turn a handled refusal into a 500.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import NoReverseMatch, reverse

logger = logging.getLogger(__name__)

# One alert per session per hour. A troll working through variants is one
# incident, not fifteen.
COOLDOWN_SECONDS = 60 * 60


def recipients():
    """Who to tell, or [] when alerting is switched off."""
    configured = getattr(settings, "CHATBOT_ABUSE_ALERT_EMAIL", "") or ""
    if isinstance(configured, (list, tuple)):
        return [str(a).strip() for a in configured if str(a).strip()]
    return [a.strip() for a in configured.split(",") if a.strip()]


def send_abuse_alert(query, moderation, request=None):
    """Notify staff that `query` was flagged and refused.

    `query` is the saved ChatbotQuery, so the email can link to it rather than
    reproducing the whole exchange in the body.
    """
    to = recipients()
    if not to:
        return False

    # Imported here rather than at module scope: the cache is a database table,
    # and importing it at startup pulls Django's app registry into a module that
    # views import at load time.
    from django.core.cache import cache

    session_key = (query.session_key or "unknown")[:40]
    cooldown_key = f"chatbot:abuse-alert:{session_key}"
    if cache.get(cooldown_key):
        logger.info("Abuse alert suppressed (cooldown) for session %s", session_key)
        return False

    try:
        subject = "[TCSP] Chatbot blocked an abusive message"
        body = _build_body(query, moderation, request)
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=to,
            fail_silently=False,
        )
    except Exception as exc:
        # Never propagate: the customer's refusal has already been decided.
        logger.error("Could not send chatbot abuse alert: %s", exc, exc_info=True)
        return False

    # Set the cooldown only after a successful send, so a failed send does not
    # silence the next hour of alerts.
    cache.set(cooldown_key, 1, COOLDOWN_SECONDS)
    logger.warning(
        "Chatbot abuse alert sent for session %s (%s)",
        session_key, moderation.category_text or "uncategorised",
    )
    return True


def _build_body(query, moderation, request):
    who = query.user.email if query.user_id else "anonymous"
    lines = [
        "The chatbot refused a message that was flagged as abusive.",
        "",
        f"When:       {query.timestamp:%Y-%m-%d %H:%M} (server time)",
        f"Bot:        {query.source}",
        f"User:       {who}",
        f"Session:    {query.session_key or 'unknown'}",
        f"Categories: {moderation.category_text or 'uncategorised'}",
        "",
        "Message:",
        f"    {' '.join((query.message or '').split())[:500]}",
        "",
        "The customer was shown a refusal. Nothing from the FAQ or the model was",
        "sent to them.",
        "",
        "Further messages from this session will be blocked and logged, but will",
        f"not trigger another email for {COOLDOWN_SECONDS // 60} minutes.",
    ]

    url = _admin_url(query, request)
    if url:
        lines += ["", f"Full history: {url}"]

    return "\n".join(lines)


def _admin_url(query, request):
    """Absolute link to this query in the general admin, or None.

    Wrapped because the admin route is the least stable thing referenced here,
    and a broken reverse() must not cost the alert.
    """
    try:
        path = reverse(
            "generaladmin:chatbot_chatbotquery_change", args=[query.pk]
        )
    except NoReverseMatch:
        return None

    if request is not None:
        return request.build_absolute_uri(path)
    return path