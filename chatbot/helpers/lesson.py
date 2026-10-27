import logging

from lessons.models import Product
from lessons_bookings.models import Term
from django.utils import timezone

from utils.context_processors import get_term_info

logger = logging.getLogger(__name__)


def format_booking_phase():
    """Which booking window is open right now, and what opens next.

    "How do I rebook?" is one of the most common questions, and the useful part
    of the answer is whether rebooking is open *today* — not a term date the
    customer has to interpret. The site already works this out for its own
    banners; the bots were only ever given raw dates.

    get_term_info takes a request purely to satisfy the context-processor
    signature and never reads it.
    """
    try:
        summary = get_term_info(None).get("phase_summary") or {}
    except Exception as exc:
        logger.error("Booking phase unavailable: %s", exc)
        return ""

    current, following = summary.get("current") or {}, summary.get("next") or {}

    # Between terms there is no phase, but the site still returns a "current"
    # entry labelled Unknown with an empty "next". Rendering those verbatim put
    # "Booking stage right now: **Unknown**" into the prompt, so a phase is only
    # included when it is genuinely identified.
    if not current.get("id") or current.get("label") in (None, "", "Unknown"):
        return ""

    lines = [
        f"- Booking stage right now: **{current['label']}**"
        + (f", until **{current['until']}**" if current.get("until") else "")
    ]
    if following.get("label"):
        lines.append(
            f"- Next stage: **{following['label']}**"
            + (f", opening **{following['starts']}**" if following.get("starts") else "")
        )
    return "\n".join(lines)


def get_upcoming_terms():
    today = timezone.now().date()
    return Term.objects.filter(end_date__gte=today).order_by("start_date")

def get_active_lessons():
    return Product.objects.filter(active=True).order_by("day_of_week", "start_time")

# How Product.get_price_for_term charges, in words. Without it the bots could
# only quote a full-term price to someone joining mid-term, who pays less.
PRICING_NOTE = (
    "- Prices are per swimmer. Booking after a term has started, you pay only for "
    "the lessons left in the term, at the per-lesson price, and never more than "
    "the full-term price."
)


def _euro(amount):
    return f"€{amount:.0f}" if amount == amount.to_integral_value() else f"€{amount:.2f}"


def _price(lesson):
    """'€12 a lesson, €132 a full term', or '' when the class has no price set."""
    parts = []
    if lesson.weekly_price:
        parts.append(f"{_euro(lesson.weekly_price)} a lesson")
    if lesson.price:
        parts.append(f"{_euro(lesson.price)} a full term")
    return ", ".join(parts)


def format_lesson_list(lessons):
    lines = []
    for lesson in lessons:
        price = _price(lesson)
        lines.append(
            f"- **{lesson.category.name}**: {lesson.get_day_of_week_display()} "
            f"{lesson.start_time.strftime('%H:%M')}–{lesson.end_time.strftime('%H:%M')} "
            f"({lesson.num_places} places{', ' + price if price else ''})"
        )
    return "\n".join(lines + [PRICING_NOTE]) if lines else ""


def format_lesson_summary(lessons):
    """One line per level: the days it runs, its times and its price.

    The chat on every page of the site is the swims bot, so most lesson
    questions arrive there, and it was given no lessons at all: asked "Price
    for lessons?", it could only say it didn't know. A line per class (over 150)
    would swamp its prompt, so it gets this summary instead.
    """
    levels = {}
    for lesson in lessons:
        level = levels.setdefault(lesson.category.name, {
            'days': set(), 'starts': [], 'ends': [], 'weekly': set(), 'term': set()})
        level['days'].add(lesson.day_of_week)
        level['starts'].append(lesson.start_time)
        level['ends'].append(lesson.end_time)
        if lesson.weekly_price:
            level['weekly'].add(lesson.weekly_price)
        if lesson.price:
            level['term'].add(lesson.price)

    def span(values):
        low, high = min(values), max(values)
        return _euro(low) if low == high else f"{_euro(low)}–{_euro(high)}"

    lines = []
    for name, level in sorted(levels.items()):
        days = ", ".join(dict(Product.DAY_CHOICES)[day][:3] for day in sorted(level['days']))
        prices = []
        if level['weekly']:
            prices.append(f"{span(level['weekly'])} a lesson")
        if level['term']:
            prices.append(f"{span(level['term'])} a full term")
        lines.append(
            f"- **{name}**: {days}, {min(level['starts']).strftime('%H:%M')}–"
            f"{max(level['ends']).strftime('%H:%M')}"
            + (f" · {', '.join(prices)}" if prices else "")
        )
    return "\n".join(lines + [PRICING_NOTE]) if lines else ""
