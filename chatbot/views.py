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

from chatbot.models import ChatbotQuery
from .helpers.faq import match_faq
from .helpers.swim import get_available_swims, format_swim_list
from .helpers.lesson import get_upcoming_terms, get_active_lessons, format_lesson_list
from chatbot.utils import get_skill_structure_summary
from .helpers.gpt import build_swim_prompt, build_lesson_prompt, parse_markdown_reply

logger = logging.getLogger(__name__)
client = OpenAI()  # Reads from OPENAI_API_KEY in environment or settings

def get_query_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
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
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert assistant helping parents understand swimming lessons, progression, and skills."},
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
            "swim times", "weekend swims", "can I swim", "sessions", "next public swim"
        ]
        if any(kw in user_message.lower() for kw in time_keywords):
            faq_answer = None
        else:
            faq_answer, confidence = match_faq(user_message, embed_func=get_query_embedding, lessons_mode=False)

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
        prompt = build_swim_prompt(user_message, swim_list, today.strftime('%A %d %B'))

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are SplashBot — help customers with swim availability, pool policies, prices and timetables."},
                {"role": "user", "content": prompt}
            ]
        )

        ChatbotQuery.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key,
            source="public_swim",
            message=user_message,
            response_type="GPT",
            confidence_score=confidence
        )

        html_reply = parse_markdown_reply(response)
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
    return JsonResponse({"reply": "This is the default chatbot endpoint. Try /chat/public-swim/ or /chat/public-lesson/."})
