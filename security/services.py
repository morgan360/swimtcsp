"""Short blocks and email alerts for attacks on the site.

Blocks are temporary on purpose. An IP address can be a whole school or mobile
network, and scanners move on anyway, so a block that lifts itself costs an
innocent neighbour an hour at most. Only unmistakable signals count: requests for
WordPress and config files this site has never had, not 404s in general, because
browsers produce plenty of those on their own.

Everything here fails open. If the cache or mail is down the site carries on.
"""
import logging
import re
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

from chatbot.helpers.alerts import recipients
from chatbot.helpers.throttle import client_ip

from .models import SecurityIncident

logger = logging.getLogger(__name__)

PROBE_PATH = re.compile(r"/wp-|/wordpress|xmlrpc|\.php$|/\.env|/\.git|phpmyadmin|^/api/", re.IGNORECASE)
PROBE_LIMIT = 5
CSRF_LIMIT = 20
ATTACK_WINDOW = 10 * 60
IP_BLOCK = 60 * 60

CHAT_FLAG_LIMIT = 3
CHAT_FLAG_WINDOW = 60 * 60
CHAT_SESSION_BLOCK = 24 * 60 * 60
CHAT_IP_BLOCK = 60 * 60

EMAILS_PER_HOUR = 5
KEEP_DAYS = 90

CHAT_UNAVAILABLE = "Chat isn't available right now. For help, please email swimming@tcsp.ie."

# BOIPA's callbacks must always arrive: a blocked one is a paid order left unpaid.
NEVER_BLOCKED = ('/boipa/',)


def _on():
    return getattr(settings, 'SECURITY_BLOCKING_ON', True)


def _count(key, window):
    """Count one event in a fixed window and return the running total."""
    if cache.add(key, 1, window):
        return 1
    try:
        return cache.incr(key)
    except ValueError:  # expired between the add and the incr
        cache.set(key, 1, window)
        return 1


def _record(kind, request, ip):
    SecurityIncident.objects.filter(created__lt=timezone.now() - timedelta(days=KEEP_DAYS)).delete()
    return SecurityIncident.objects.create(kind=kind, ip=ip[:45], path=request.path[:200])


def _alert(incident, what):
    """Email about a block, capped so a wave of scanners can't flood the inbox."""
    to = recipients()
    if not to or _count('security:emails', 60 * 60) > EMAILS_PER_HOUR:
        return
    send_mail(
        subject=f"[TCSP] {incident.get_kind_display()}: {incident.ip}",
        message=(f"{what}\n\nAddress: {incident.ip}\nLast path: {incident.path}\n"
                 f"When: {timezone.localtime(incident.created):%a %d %b %H:%M}\n\n"
                 f"This lifts itself. No action needed unless it keeps happening: "
                 f"see Security on the Live Dashboard.\n"),
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        recipient_list=to,
        fail_silently=False,
    )


def is_exempt(request):
    return request.path.startswith(NEVER_BLOCKED)


def ip_is_blocked(request):
    try:
        return _on() and not is_exempt(request) and bool(cache.get(f'security:block:{client_ip(request)}'))
    except Exception as exc:
        logger.error("Could not check an IP block: %s", exc)
        return False


def _strike(request, name, limit, kind, what):
    """Count an attack signal from this address, blocking it at the limit."""
    if not _on() or is_exempt(request):
        return
    try:
        ip = client_ip(request)
        if not ip or ip in getattr(settings, 'SECURITY_IP_ALLOWLIST', ()):
            return
        # == so that a burst blocks, records and emails once.
        if _count(f'security:{name}:{ip}', ATTACK_WINDOW) == limit:
            cache.set(f'security:block:{ip}', 1, IP_BLOCK)
            _alert(_record(kind, request, ip), what)
    except Exception as exc:
        logger.error("Could not record a security strike: %s", exc)


def note_response(request, status):
    """Called for every response: count requests for files a scanner looks for."""
    if status == 404 and PROBE_PATH.search(request.path):
        _strike(request, 'probe', PROBE_LIMIT, SecurityIncident.PROBE_BLOCKED,
                "An address looking for WordPress or config files has been blocked from the whole site for an hour.")


def note_csrf_failure(request):
    _strike(request, 'csrf', CSRF_LIMIT, SecurityIncident.CSRF_BLOCKED,
            "An address sending a burst of forged form submissions has been blocked from the whole site for an hour.")


def chat_is_blocked(request):
    try:
        if not _on():
            return False
        return bool(cache.get_many([f'security:chat:session:{request.session.session_key}',
                                    f'security:chat:ip:{client_ip(request)}']))
    except Exception as exc:
        logger.error("Could not check a chat block: %s", exc)
        return False


def note_chat_refusal(request):
    """Record a refused chat message, blocking the chat at the limit. Counted by
    session and by address, because dropping the cookie makes a new session."""
    try:
        ip = client_ip(request)
        _record(SecurityIncident.CHAT_REFUSED, request, ip)
        if not _on():
            return
        session = request.session.session_key
        by_session = _count(f'security:chatflags:session:{session}', CHAT_FLAG_WINDOW)
        by_ip = _count(f'security:chatflags:ip:{ip}', CHAT_FLAG_WINDOW)
        if CHAT_FLAG_LIMIT in (by_session, by_ip):
            cache.set(f'security:chat:session:{session}', 1, CHAT_SESSION_BLOCK)
            cache.set(f'security:chat:ip:{ip}', 1, CHAT_IP_BLOCK)
            _alert(_record(SecurityIncident.CHAT_BLOCKED, request, ip),
                   f"After {CHAT_FLAG_LIMIT} refused messages, this chat session is blocked for 24 hours "
                   f"and this address from the chat for an hour. The rest of the site still works for them.")
    except Exception as exc:
        logger.error("Could not record a chat refusal: %s", exc)
