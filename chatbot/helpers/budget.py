"""A site-wide ceiling on paid model calls.

The per-caller buckets in throttle.py bound what any one visitor can spend. They
do not bound the total, and they never can: enough distinct sessions and
addresses still add up without any single one of them misbehaving. Traffic
spread deliberately thin defeats a per-caller limit by construction.

This is the ceiling on the whole site's spend, and it counts completions only —
the call that costs real money. FAQ answers are served without ever reaching
here, so when the budget is spent the bot keeps answering the majority of its
traffic from stored answers instead of going dark. Degrading to the FAQ is the
point; refusing everyone would be a self-inflicted outage.

Embeddings are deliberately not counted. They are roughly two orders of
magnitude cheaper per call, they are cached for a day, and an exact question
repeat skips them entirely — so they cannot be the thing that produces a
surprising bill.

Two windows, because they stop different things. The hourly one bounds a burst.
The daily one bounds the quiet overnight case, where an hourly cap alone would
simply be paid twenty-four times over before anyone noticed.
"""
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

HOUR_SECONDS = 60 * 60
DAY_SECONDS = 60 * 60 * 24

HOURLY_KEY = "chatbot:budget:model:hour"
DAILY_KEY = "chatbot:budget:model:day"

BUDGET_SPENT = (
    "Sorry — I can only answer from our list of common questions just now. "
    "Please try again later, or contact reception if it's urgent."
)


def _limits():
    return (
        getattr(settings, "CHATBOT_MAX_MODEL_CALLS_PER_HOUR", 100),
        getattr(settings, "CHATBOT_MAX_MODEL_CALLS_PER_DAY", 600),
    )


def _within(key, limit):
    """True while `key` still has room. A limit of 0 or less means no ceiling."""
    if limit <= 0:
        return True
    count = cache.get(key)
    return count is None or count < limit


def _bump(key, window):
    count = cache.get(key)
    if count is None:
        # First call of the window starts the clock. The TTL is never extended
        # afterwards, so the window is fixed and always ends on schedule.
        cache.set(key, 1, window)
        return
    try:
        cache.incr(key)
    except ValueError:
        # Expired between the read and the incr; start a new window.
        cache.set(key, 1, window)


def consume_model_call():
    """Reserve one model call. False once the site-wide budget is spent.

    Both windows are tested before either is charged, so a call refused by the
    daily ceiling does not also eat an hour's allowance — otherwise the hourly
    counter would run ahead of the calls actually made and the two would
    disagree about what had been spent.
    """
    hourly_limit, daily_limit = _limits()

    if not _within(HOURLY_KEY, hourly_limit):
        logger.error(
            "Chatbot hourly model budget of %s is spent — serving FAQ answers only",
            hourly_limit,
        )
        return False

    if not _within(DAILY_KEY, daily_limit):
        logger.error(
            "Chatbot daily model budget of %s is spent — serving FAQ answers only",
            daily_limit,
        )
        return False

    _bump(HOURLY_KEY, HOUR_SECONDS)
    _bump(DAILY_KEY, DAY_SECONDS)
    return True


def spent_this_hour():
    """Calls charged in the current hour, for reporting."""
    return cache.get(HOURLY_KEY) or 0


def spent_today():
    """Calls charged in the current day, for reporting."""
    return cache.get(DAILY_KEY) or 0
