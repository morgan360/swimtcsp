"""Screening for abusive input, applied before anything else looks at a message.

Why this exists, specifically:

In July 2026 the bot answered "Yes!." to "Can I sexually assault people and kill
people in the shower", and to several variants about children in the changing
rooms. Nothing was broken in the sense of throwing an error. The FAQ entry "Are
there showers available?" opens with a bare "Yes!.", the retrieval tier serves
stored answers *verbatim with no model call*, and any message containing
"shower" retrieved it. The model — the only component applying any judgement —
was never reached. From the same session, "Can I make a bomb threat" scored below
the threshold, went to the model, and was properly refused.

So the FAQ tier was a model bypass, and therefore a safety bypass. Raising the
retrieval thresholds on 2026-08-07 closed it by side effect, which is not the
same as fixing it: the safety property was left resting on similarity scores
staying high, and any threshold change or FAQ edit could hand it back.

This module makes the check independent of retrieval. It runs *before*
match_faq, so it covers the FAQ tier and the model tier equally, and it does not
care what any entry happens to score.

Fails open, deliberately. If the moderation endpoint is unreachable the message
is allowed through to the model, which applies its own judgement — the layer
that was already refusing bomb threats. The alternative, refusing everyone
during an OpenAI outage, would take the whole bot down for ordinary customers to
guard against an abuser who is not currently present. The failure is logged at
warning so an outage is visible rather than silent.
"""
import logging

from django.conf import settings

from chatbot.helpers import client

logger = logging.getLogger(__name__)

# Free to call and not counted against the spend cap in budget.py, which covers
# completions only. Screening every message therefore costs nothing.
MODERATION_MODEL = "omni-moderation-latest"

REFUSAL = (
    "I can only help with questions about swimming at the pool — sessions, "
    "lessons, prices, booking and facilities. If you need to talk to someone, "
    "please contact reception."
)


class ModerationResult:
    """The outcome of one screening call.

    `categories` is kept even when nothing is flagged so that callers can log a
    consistent shape, and so a category list is available for the alert email
    without a second call.
    """

    def __init__(self, flagged=False, categories=None, checked=True):
        self.flagged = flagged
        self.categories = categories or []
        # False when the call could not be made at all — distinguishes "screened
        # and clean" from "not screened", which matters when reading the logs
        # back after an outage.
        self.checked = checked

    @property
    def category_text(self):
        return ", ".join(self.categories)


def is_enabled():
    return getattr(settings, "CHATBOT_MODERATION_ENABLED", True)


def check(text):
    """Screen one user message. Never raises."""
    if not is_enabled() or not (text or "").strip():
        return ModerationResult(checked=False)

    try:
        response = client.get_client().moderations.create(
            model=MODERATION_MODEL,
            input=text,
        )
        result = response.results[0]
    except Exception as exc:
        # Fail open — see the module docstring.
        logger.warning("Moderation unavailable, allowing message through: %s", exc)
        return ModerationResult(checked=False)

    if not result.flagged:
        return ModerationResult(flagged=False)

    # The SDK returns an object whose truthy attributes are the categories that
    # fired. Sorted so the same set always reads the same way in logs and email.
    categories = sorted(
        name for name, hit in _category_items(result) if hit
    )
    return ModerationResult(flagged=True, categories=categories)


def _category_items(result):
    """(name, hit) pairs from a moderation result, across SDK shapes.

    Older SDKs expose `.categories` as a pydantic model, newer ones as something
    dict-like. Both appear across the environments this runs in, and a crash
    here would fail open on a message that was actually flagged — the one case
    where failing open is not acceptable.
    """
    categories = getattr(result, "categories", None)
    if categories is None:
        return []

    if hasattr(categories, "model_dump"):
        return list(categories.model_dump().items())
    if hasattr(categories, "dict"):
        return list(categories.dict().items())
    if isinstance(categories, dict):
        return list(categories.items())
    return [
        (name, getattr(categories, name))
        for name in dir(categories)
        if not name.startswith("_") and isinstance(getattr(categories, name), bool)
    ]