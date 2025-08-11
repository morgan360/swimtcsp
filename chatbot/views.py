import os
import json
import logging
import markdown
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.utils import timezone
from openai import OpenAI
from lessons_bookings.models import Term

from chatbot.models import ChatbotQuery
from .helpers.faq import match_faq
from .helpers.swim import get_available_swims, format_swim_list
from .helpers.lesson import get_upcoming_terms, get_active_lessons, format_lesson_list
from chatbot.utils import get_skill_structure_summary
from .helpers.gpt import build_swim_prompt, build_lesson_prompt, parse_markdown_reply

logger = logging.getLogger(__name__)

# Initialise OpenAI client – will pick up key from env
client = OpenAI()

# Read model names from env or Django settings, with sensible defaults
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", getattr(settings, "OPENAI_CHAT_MODEL", "gpt-4o-mini"))
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", getattr(settings, "OPENAI_EMBED_MODEL", "text-embedding-3-small"))

def get_query_embedding(text):
    response = client.embeddings.create(
        input=text,
        model=EMBED_MODEL
    )
    return response.data[0].embedding


# ✅ PUBLIC LESSON CHATBOT VIEW
@csrf_exempt
def public_lesson_chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()
        logger.info("📩 Lesson bot message: %s", user_message)
        faq_answer, confidence = match_faq(user_message, embed_func=get_query_embedding, lessons_mode=True)

        if faq_answer:
            logger.info("✅ Responding from FAQ")
            ChatbotQuery.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key,
                source="public_lesson",
                message=user_message,
                response_type="FAQ",
                confidence_score=confidence
            )
            html_reply = markdown.markdown(faq_answer, extensions=["extra"])
            return JsonResponse({"reply": html_reply})

        terms = get_upcoming_terms()
        lessons = get_active_lessons()
        term_info = "\n".join([
            f"- **Term** from **{t.start_date}** to **{t.end_date}**"
            for t in terms
        ]) or "No upcoming terms available."
        lesson_list = format_lesson_list(lessons) or "No active public lessons found."

        try:
            skill_summary = get_skill_structure_summary()
        except Exception as e:
            logger.error("❌ Skill summary failed: %s", e)
            skill_summary = "*Skill summary temporarily unavailable.*"

        prompt = build_lesson_prompt(user_message, term_info, lesson_list, skill_summary)
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system",
                 "content": "You are an expert assistant helping parents understand swimming lessons, progression, and skills."},
                {"role": "user", "content": prompt}
            ]
        )

        html_reply = parse_markdown_reply(response)
        ChatbotQuery.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            source="public_lesson",
            message=user_message,
            response_type="GPT",
            confidence_score=confidence
        )
        return JsonResponse({"reply": html_reply})

    except Exception as e:
        logger.error("❌ Lesson chatbot error: %s", str(e), exc_info=True)
        return JsonResponse({"reply": f"⚠️ Error: {str(e)}"}, status=200)


# ✅ PUBLIC SWIM CHATBOT VIEW
@csrf_exempt
def public_swim_chat(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()
        logger.info("📩 Swim bot message: %s", user_message)

        # Ensure session exists
        if not request.session.session_key:
            request.session.save()

        confidence = None
        time_keywords = [
            "when is the next swim", "what swims are available", "swim today",
            "swim times", "weekend swims", "can I swim", "sessions", "next public swim",
            "lesson", "term", "rebooking", "booking", "assessment", "swim term"
        ]
        if any(kw in user_message.lower() for kw in time_keywords):
            faq_answer = None
        else:
            faq_answer, confidence = match_faq(
                user_message,
                embed_func=get_query_embedding,
                lessons_mode=False
            )

        if faq_answer:
            logger.info("✅ Responding from FAQ")
            ChatbotQuery.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key,
                source="public_swim",
                message=user_message,
                response_type="FAQ",
                confidence_score=confidence
            )
            html_reply = markdown.markdown(faq_answer, extensions=["extra"])
            return JsonResponse({"reply": html_reply})

        swims = get_available_swims()
        swim_list = format_swim_list(swims)
        today = timezone.now().date()
        current_term = Term.get_current_term()
        next_term = Term.get_next_term()

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
        if current_term:
            lesson_term_info += format_term_info(current_term, "Current lesson term") + "\n\n"
        if next_term:
            lesson_term_info += format_term_info(next_term, "Next lesson term")

        swim_prompt = build_swim_prompt(user_message, swim_list, today.strftime('%A %d %B'))
        full_prompt = (
            f"You may find this lesson term info useful:\n\n{lesson_term_info}\n\n"
            f"{swim_prompt}"
        )

        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": """
You are SplashBot — a helpful assistant who answers questions about public swims and lessons.
You have access to lesson term dates, including rebooking, booking, and assessment dates.
Use this info to answer when customers can book, rebook, or plan lessons.
"""
                },
                {"role": "user", "content": full_prompt}
            ]
        )

        try:
            raw_reply = response.choices[0].message.content
            logger.info("🧠 GPT says:\n%s", raw_reply)
            html_reply = markdown.markdown(raw_reply, extensions=["extra"])
        except Exception as e:
            logger.error("⚠️ Failed to parse GPT reply: %s", e)
            html_reply = "⚠️ Sorry, I didn’t understand that. Please try again."

        ChatbotQuery.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            source="public_swim",
            message=user_message,
            response_type="GPT",
            confidence_score=confidence
        )

        return JsonResponse({"reply": html_reply})

    except Exception as e:
        logger.error("❌ Swim chatbot error: %s", str(e), exc_info=True)
        return JsonResponse({"error": "Something went wrong while processing your message."}, status=500)



# ✅ UI ROUTES
def public_lesson_chat_ui(request):
    return render(request, "chatbot/public_lesson_chat.html")


def public_swim_chat_ui(request):
    return render(request, "chatbot/public_swim_chat.html")


def chat_response(request):
    return JsonResponse(
        {"reply": "This is the default chatbot endpoint. Try /chat/public-swim/ or /chat/public-lesson/."})
