import bleach
import markdown

# Model output is rendered as HTML, so it is sanitised. FAQ answers are
# admin-authored through CKEditor and stay trusted.
ALLOWED_TAGS = [
    "p", "br", "strong", "b", "em", "i", "u", "ul", "ol", "li",
    "a", "h2", "h3", "h4", "blockquote", "code", "pre", "table",
    "thead", "tbody", "tr", "th", "td",
]
ALLOWED_ATTRS = {"a": ["href", "title", "target", "rel"]}


def _context_block(faq_context):
    """A grounding block built from retrieved FAQs, or '' when none matched."""
    if not faq_context:
        return ""
    return f"""
📋 Verified answers from our FAQ (prefer these over general knowledge,
especially for prices, ages and policies):

{faq_context}
"""


def build_swim_prompt(user_message, swim_list, today_str, faq_context=""):
    return f"""
You are a helpful assistant for a swimming pool website.

Today is {today_str}. The user may be asking about:

- Swim session availability
- Prices, booking, or payment
- Types of swims (e.g. public, family)
- Facility info (e.g. lockers, swimming hats)

If the user is asking about swim **times or availability**, answer based on this list of current swim sessions:

{swim_list}
{_context_block(faq_context)}
If the question is more general (about payment, facilities, requirements, etc.), respond clearly based on the verified answers above where they apply. If you do not know, say so and suggest contacting reception — do not invent prices, times or policies.

User asked: \"{user_message}\"

Please respond in markdown using bold, bullet points or paragraphs where appropriate. Do not reference sessions that aren't listed above. Keep the answer under 150 words.
"""


def build_lesson_prompt(user_message, term_info, lesson_list, skill_summary="", faq_context=""):
    skill_block = f"\n🏊 Skill Structure by Core Aquatic Skill:\n{skill_summary}\n" if skill_summary else ""
    return f"""
You are a helpful assistant for a swimming lesson booking website.

🏫 Teaching Philosophy:
Our swimming programme is built around Core Aquatic Skills (CAS), such as Aquatic Breathing, Floatation & Buoyancy, Rotation & Balance, and Movement Coordination.

Children progress through structured levels (e.g. Beginners 1, Beginners 2, Improvers...) by consistently demonstrating these skills, not by age or number of terms completed.

You may see the same CAS taught across multiple levels, but in more advanced forms — e.g. in deeper water, with less support, or in more dynamic situations. This repetition is intentional and crucial for confident, safe swimming.

It's normal (and often beneficial) for a swimmer to repeat a level before advancing.

📅 Upcoming Term Dates:
{term_info}

📘 Available Lessons:
{lesson_list}
{skill_block}{_context_block(faq_context)}
User asked: \"{user_message}\"

Please give a friendly and clear answer based on the information above. If you do not know, say so and suggest contacting reception — do not invent prices, times or policies. Use markdown formatting where appropriate and keep the answer under 150 words.
"""


def render_model_markdown(text):
    """Model output → sanitised HTML."""
    html = markdown.markdown((text or "").strip(), extensions=["extra"])
    return bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


def render_faq_markdown(text):
    """FAQ answer → HTML. Admin-authored, so markup is preserved as written."""
    return markdown.markdown((text or "").strip(), extensions=["extra"])
