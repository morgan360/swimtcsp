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

def format_lesson_list(lessons):
    return "\n".join([
        f"- **{lesson.category.name}**: {lesson.get_day_of_week_display()} {lesson.start_time.strftime('%H:%M')}–{lesson.end_time.strftime('%H:%M')} ({lesson.num_places} places)"
        for lesson in lessons
    ])
