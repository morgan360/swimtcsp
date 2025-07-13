import openai
import json
import logging
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.utils import timezone
from swims.models import PublicSwimProduct
import pytz
import markdown
from datetime import datetime, time

from lessons_bookings.models import Term
from lessons.models import Product, Category  # or wherever your lessons are
from .utils import get_skill_structure_summary

# Setup
logger = logging.getLogger(__name__)
client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
def public_lesson_chat_ui(request):
    return render(request, "chatbot/public_lesson_chat.html")

@csrf_exempt
def public_lesson_chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()
        logger.info("📩 Lesson bot message: %s", user_message)

        # 📅 Get current and upcoming terms
        today = timezone.now().date()
        terms = Term.objects.filter(end_date__gte=today).order_by("start_date")

        term_info = "\n".join([
            f"- **Term** from **{t.start_date}** to **{t.end_date}**"
            for t in terms
        ]) or "No upcoming terms available."

        # 📘 Get active lessons
        lessons = Product.objects.filter(active=True).order_by("day_of_week", "start_time")

        lesson_list = "\n".join([
            f"- **{lesson.category.name}**: {lesson.get_day_of_week_display()} {lesson.start_time.strftime('%H:%M')}–{lesson.end_time.strftime('%H:%M')} ({lesson.num_places} places)"
            for lesson in lessons
        ]) or "No active public lessons found."

        # 🧠 Add skill structure summary
        try:
            skill_summary = get_skill_structure_summary()
        except Exception as e:
            logger.error("❌ Skill summary failed: %s", e)
            skill_summary = "*Skill summary temporarily unavailable.*"

        # 🧠 Prompt to GPT
        prompt = f"""
You are a helpful assistant for a swimming lesson booking website.

🏫 Teaching Philosophy:
Our swimming programme is built around Core Aquatic Skills (CAS), such as Aquatic Breathing, Floatation & Buoyancy, Rotation & Balance, and Movement Coordination.

Children progress through structured levels (e.g. Beginners 1, Beginners 2, Improvers...) by consistently demonstrating these skills, not by age or number of terms completed.

You may see the **same CAS taught across multiple levels**, but in more advanced forms — e.g. in deeper water, with less support, or in more dynamic situations. This repetition is **intentional** and crucial for confident, safe swimming.

It’s normal (and often beneficial) for a swimmer to repeat a level before advancing.

📅 Upcoming Term Dates:
{term_info}

📘 Available Lessons:
{lesson_list}

🏊 Skill Structure by Core Aquatic Skill:
{skill_summary}

User asked: "{user_message}"

Please give a friendly and clear answer based on the information above. Use markdown formatting and explain our teaching process, skill goals, and why progression may take time.
"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert assistant helping parents understand swimming lessons, progression, and skills."},
                {"role": "user", "content": prompt}
            ]
        )

        reply = response.choices[0].message.content.strip()
        html_reply = markdown.markdown(reply, extensions=["extra"])

        return JsonResponse({"reply": html_reply})

    except Exception as e:
        logger.error("❌ Lesson chatbot error: %s", str(e), exc_info=True)
        return JsonResponse({"reply": f"⚠️ Error: {str(e)}"}, status=200)

######################################################################################################

# 📁 Load FAQ markdown content from file
def load_booking_faq():
    path = Path(__file__).resolve().parent / "static" / "chatbot" / "faq_booking.md"
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error("❌ Could not read FAQ markdown file: %s", e)
        return "Sorry, booking information is currently unavailable."

# 🔹 Fallback/default chatbot response
def chat_response(request):
    return JsonResponse({
        "reply": "This is the generic chatbot endpoint. Please use /chat/public-swim/ for swim queries."
    })

# 🔹 Load the web UI for the chatbot
def public_swim_chat_ui(request):
    return render(request, "chatbot/public_swim_chat.html")

# 🔹 Core chatbot view with booking + swim logic
@csrf_exempt
def public_swim_chat(request):
    def get_price_table(product):
        prices = product.price_variants.all()
        if not prices:
            return ""
        price_lines = [f"  - {pv.get_variant_display()}: €{pv.price:.2f}" for pv in prices]
        return f"\n**Prices:**\n" + "\n".join(price_lines)

    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()
        logger.info("📩 User message: %s", user_message)

        # 📌 Check if the question is about booking or payment
        booking_keywords = [
            "book", "booking", "sign up", "sign-up", "signup", "payment",
            "credit card", "secure", "security", "qr", "door", "walk-in", "pay"
        ]
        if any(keyword in user_message.lower() for keyword in booking_keywords):
            booking_reply = load_booking_faq()
            html_reply = markdown.markdown(booking_reply, extensions=["extra"])
            return JsonResponse({"reply": html_reply})

        # 📅 Get current day in Europe/Dublin timezone
        dublin = pytz.timezone("Europe/Dublin")
        today = timezone.now().astimezone(dublin).date()
        today_weekday = today.weekday()  # Monday=0

        # 🔍 Fetch all available swims
        all_swims = PublicSwimProduct.objects.filter(
            available=True
        ).order_by("day_of_week", "start_time")
        # Get current time in Dublin
        now = timezone.now().astimezone(dublin)
        current_time = now.time()

        filtered_swims = []

        for swim in all_swims:
            if swim.day_of_week == today_weekday:
                if swim.end_time > current_time:
                    filtered_swims.append(swim)
            else:
                filtered_swims.append(swim)
        # Prioritise today's remaining swims
        sorted_swims = sorted(
            filtered_swims,
            key=lambda s: (0 if s.day_of_week == today_weekday else 1, s.day_of_week, s.start_time)
        )

        # 🌟 Filter to public swims only if specifically requested
        user_wants_public = "public" in user_message.lower()
        filtered_swims = [s for s in sorted_swims if "public" in s.name.lower()] if user_wants_public else sorted_swims
        upcoming_swims = filtered_swims[:15]

        # 🧾 Format the session info for GPT
        swim_list = "\n\n".join([
            f"- **{s.name}** on **{s.get_day_of_week_display()}** from **{s.start_time.strftime('%H:%M')}** to **{s.end_time.strftime('%H:%M')}** – **{s.num_places} places available**\n{get_price_table(s)}"
            for s in upcoming_swims
        ])

        logger.info("🧾 Swim list passed to GPT:\n%s", swim_list)

        # 💬 Construct the GPT prompt
        full_prompt = f"""
        You are a helpful assistant for a swimming pool website.
        Today is {today.strftime('%A %d %B')}.

        The user wants to know about available swims.

        Here is the current list of available swim sessions in markdown list format:

        {swim_list}

        User asked: \"{user_message}\"

        Please respond using markdown formatting (bold, lists) to clearly present the info.
        Only include sessions based on the list above. If there are no sessions today, say so clearly.
        <example>
        User asked: "What are the next 10 swims?"
        swim_list:  [name, day, start_time, end_time, num_places]
        Bot responded: "There are no swims today. Please come back tomorrow."
        </example>
        """

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Answer customer questions about swim availability."},
                {"role": "user", "content": full_prompt}
            ]
        )

        reply = response.choices[0].message.content.strip()
        logger.info("🤖 GPT reply: %s", reply)

        html_reply = markdown.markdown(reply, extensions=["extra"])
        return JsonResponse({"reply": html_reply})

    except Exception as e:
        logger.error("❌ Chatbot error: %s", str(e), exc_info=True)
        return JsonResponse({"error": "Something went wrong while processing your message."}, status=500)
