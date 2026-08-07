import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from lessons_bookings.models import Term

from chatbot.models import ChatbotQuery
from chatbot.utils import get_skill_structure_summary
from .helpers import faq as faq_helper
from .helpers.client import ask_openai
from .helpers.gpt import (
    build_lesson_prompt,
    build_swim_prompt,
    render_faq_markdown,
    render_model_markdown,
)
from .helpers.lesson import format_lesson_list, get_active_lessons, get_upcoming_terms
from .helpers.swim import format_swim_list, get_available_swims
from .helpers.throttle import TOO_MANY_MESSAGES, is_rate_limited

logger = logging.getLogger(__name__)

# Questions whose answer depends on live session data, which no stored FAQ can
# hold. Kept deliberately narrow: the old list included "booking", "lesson" and
# "sessions", which sent straight-up FAQ questions like "How do I book a
# lesson?" to the model for no reason.
LIVE_DATA_KEYWORDS = (
    # When
    "today", "tomorrow", "tonight", "this week", "weekend",
    "when is", "when's", "whens", "when are", "when can", "when do",
    "what time", "times", "timetable", "schedule",
    # Which session, on which day — the phrasings real traffic actually uses
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "next swim", "next public swim", "what swims", "any swims",
    # Capacity
    "available", "availability", "places left", "spaces", "fully booked",
)


# The skill tree renders to ~11 KB (roughly 3k tokens). It is the answer to
# "why hasn't my child moved up", and noise for "how do I pay", so it is only
# attached when the question is actually about progression.
PROGRESSION_KEYWORDS = (
    "level", "levels", "move up", "moved up", "move-up", "moving up",
    "progress", "progression", "advance", "next stage", "stage",
    "skill", "skills", "ready", "assess", "assessment", "repeat",
    "badge", "beginner", "improver", "widths", "lengths",
)


def _needs_live_data(message):
    return any(keyword in message for keyword in LIVE_DATA_KEYWORDS)


def _is_progression_question(message):
    return any(keyword in message for keyword in PROGRESSION_KEYWORDS)


def _read_message(request):
    """Extract and bound the user's message. Returns (message, error_response)."""
    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        return None, JsonResponse({"error": "Invalid request body."}, status=400)

    message = (data.get("message") or "").strip()
    if not message:
        return None, JsonResponse({"error": "Please type a question."}, status=400)

    # Bound the text before it reaches the embedding or completion API.
    return message[: settings.CHATBOT_MAX_MESSAGE_CHARS], None


def _log_query(request, source, message, response, response_type, score):
    ChatbotQuery.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key or "",
        source=source,
        message=message,
        response=response,
        response_type=response_type,
        confidence_score=score,
    )


def _prepare(request):
    """Shared entry checks. Returns (message, error_response)."""
    if request.method != "POST":
        return None, JsonResponse({"error": "Invalid request method"}, status=405)

    if not request.session.session_key:
        request.session.save()

    if is_rate_limited(request):
        return None, JsonResponse({"reply": f"<p>{TOO_MANY_MESSAGES}</p>"}, status=429)

    return _read_message(request)


# ✅ PUBLIC LESSON CHATBOT VIEW
def public_lesson_chat_api(request):
    user_message, error = _prepare(request)
    if error:
        return error

    logger.debug("Lesson bot message received (%d chars)", len(user_message))

    try:
        result = faq_helper.match_faq(user_message, lessons_mode=True)

        if result.is_answered:
            html_reply = render_faq_markdown(result.answer)
            _log_query(
                request, "public_lesson", user_message,
                result.answer, result.tier, result.score,
            )
            return JsonResponse({"reply": html_reply})

        terms = get_upcoming_terms()
        term_info = "\n".join(
            f"- **Term** from **{t.start_date}** to **{t.end_date}**" for t in terms
        ) or "No upcoming terms available."
        lesson_list = format_lesson_list(get_active_lessons()) or "No active public lessons found."

        skill_summary = ""
        if _is_progression_question(user_message.lower()):
            try:
                skill_summary = get_skill_structure_summary()
            except Exception as exc:
                logger.error("Skill summary failed: %s", exc)

        prompt = build_lesson_prompt(
            user_message,
            term_info,
            lesson_list,
            skill_summary=skill_summary,
            faq_context=faq_helper.format_context(result.context),
        )
        raw_reply, api_error = ask_openai([
            {
                "role": "system",
                "content": "You are an expert assistant helping parents understand swimming lessons, progression, and skills.",
            },
            {"role": "user", "content": prompt},
        ])

        if api_error:
            return JsonResponse({"reply": f"<p>{api_error}</p>"}, status=503)

        _log_query(
            request, "public_lesson", user_message,
            raw_reply, result.tier, result.score,
        )
        return JsonResponse({"reply": render_model_markdown(raw_reply)})

    except Exception as exc:
        logger.error("Lesson chatbot error: %s", exc, exc_info=True)
        return JsonResponse(
            {"error": "Something went wrong while processing your message."},
            status=500,
        )


# ✅ PUBLIC SWIM CHATBOT VIEW
def public_swim_chat(request):
    user_message, error = _prepare(request)
    if error:
        return error

    logger.debug("Swim bot message received (%d chars)", len(user_message))

    try:
        result = faq_helper.match_faq(user_message, lessons_mode=False)

        # A confident FAQ answers most things — but anything that depends on
        # today's timetable has to go to the live-data path instead.
        if result.is_answered and not _needs_live_data(user_message.lower()):
            html_reply = render_faq_markdown(result.answer)
            _log_query(
                request, "public_swim", user_message,
                result.answer, result.tier, result.score,
            )
            return JsonResponse({"reply": html_reply})

        swim_list = format_swim_list(get_available_swims())
        today = timezone.now().date()

        def format_term_info(term, label):
            if not term:
                return f"{label}: No data available."
            return (
                f"{label} (ID {term.id}) runs from {term.start_date.strftime('%d %b %Y')} to {term.end_date.strftime('%d %b %Y')}.\n"
                f"- Rebooking opens: {term.rebooking_date.strftime('%d %b %Y') if term.rebooking_date else 'TBA'}\n"
                f"- Public booking opens: {term.booking_date.strftime('%d %b %Y') if term.booking_date else 'TBA'}\n"
                f"- Assessments: {term.assessment_date.strftime('%d %b %Y') if term.assessment_date else 'TBA'}"
            )

        lesson_term_info = ""
        current_term = Term.get_current_term()
        next_term = Term.get_next_term()
        if current_term:
            lesson_term_info += format_term_info(current_term, "Current lesson term") + "\n\n"
        if next_term:
            lesson_term_info += format_term_info(next_term, "Next lesson term")

        swim_prompt = build_swim_prompt(
            user_message,
            swim_list,
            today.strftime("%A %d %B"),
            faq_context=faq_helper.format_context(result.context),
        )
        full_prompt = (
            f"You may find this lesson term info useful:\n\n{lesson_term_info}\n\n"
            f"{swim_prompt}"
        )

        raw_reply, api_error = ask_openai([
            {
                "role": "system",
                "content": (
                    "You are SplashBot — a helpful assistant who answers questions about "
                    "public swims and lessons.\nYou have access to lesson term dates, "
                    "including rebooking, booking, and assessment dates.\nUse this info to "
                    "answer when customers can book, rebook, or plan lessons."
                ),
            },
            {"role": "user", "content": full_prompt},
        ])

        if api_error:
            return JsonResponse({"reply": f"<p>{api_error}</p>"}, status=503)

        _log_query(
            request, "public_swim", user_message,
            raw_reply, faq_helper.MISS, result.score,
        )
        return JsonResponse({"reply": render_model_markdown(raw_reply)})

    except Exception as exc:
        logger.error("Swim chatbot error: %s", exc, exc_info=True)
        return JsonResponse(
            {"error": "Something went wrong while processing your message."},
            status=500,
        )


# ✅ UI ROUTES
# ensure_csrf_cookie: these pages contain no form, so without it there is no
# csrftoken cookie for chat.js to send and every POST would be rejected.
@ensure_csrf_cookie
def public_lesson_chat_ui(request):
    return render(request, "chatbot/public_lesson_chat.html")


@ensure_csrf_cookie
def public_swim_chat_ui(request):
    return render(request, "chatbot/public_swim_chat.html")


def chat_response(request):
    return JsonResponse(
        {"reply": "This is the default chatbot endpoint. Try /chat/public-swim/ or /chat/public-lesson/."})
