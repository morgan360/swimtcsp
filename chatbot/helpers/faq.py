"""FAQ retrieval, in three tiers.

Matching used to be an either/or gate: above the threshold it returned the
stored answer, below it returned nothing and the caller asked the model with no
FAQ context at all — so weak-but-relevant entries were thrown away and the
model answered pricing and policy questions from thin air.

Now a single embedding produces one of three outcomes:

    MATCH   score >= FAQ_MATCH_THRESHOLD   serve the answer verbatim, no model call
    HEDGED  score >= FAQ_MIN_CONFIDENCE    serve it, flagged as uncertain
    MISS    below that                     call the model, with any entry above
                                           FAQ_CONTEXT_MIN_SCORE as grounding
"""
import logging

from django.conf import settings
from django.core.cache import cache
from django.utils.html import strip_tags

from chatbot.helpers import client
from chatbot.helpers.faq_index import (
    get_index,
    query_cache_key,
    query_text,
)

logger = logging.getLogger(__name__)

MATCH = "FAQ"
HEDGED = "FAQ_HEDGED"
MISS = "GPT"

HEDGE_PREFIX = "<p><em>I'm not certain, but this may help:</em></p>"

QUERY_EMBED_TTL = 60 * 60 * 24


class FAQResult:
    """The outcome of one FAQ lookup.

    `tier` doubles as ChatbotQuery.response_type, so the effect of threshold
    changes is visible in the logged traffic.
    """

    def __init__(self, tier, answer=None, score=None, context=None):
        self.tier = tier
        self.answer = answer
        self.score = score
        self.context = context or []

    @property
    def is_answered(self):
        return self.tier in (MATCH, HEDGED)


def embed_query(user_message):
    """Embedding for a user message, cached by normalised text.

    Repeated questions — which is most of the traffic — then cost no API call
    and skip the round-trip latency.
    """
    key = query_cache_key(user_message)
    cached = cache.get(key)
    if cached is not None:
        return cached

    vector = client.embed(query_text(user_message))
    if vector is not None:
        cache.set(key, vector, QUERY_EMBED_TTL)
    return vector


def match_faq(user_message, lessons_mode=False, embed_func=None, top_k=5):
    """Look up `user_message` against the FAQ corpus.

    `embed_func` is injectable so tests can score against fixed vectors without
    touching the API.
    """
    index = get_index()
    if not len(index):
        return FAQResult(MISS)

    exact = index.exact_match(user_message, lessons_mode)
    if exact:
        logger.debug("FAQ exact-text hit, no embedding needed")
        return FAQResult(
            MATCH,
            answer=exact["answer"],
            score=1.0,
            context=relevant_context([(1.0, exact)]),
        )

    embed_func = embed_func or embed_query
    vector = embed_func(user_message)
    if vector is None:
        # Embeddings unavailable — answer without grounding rather than fail.
        return FAQResult(MISS)

    scored = index.search(vector, lessons_mode, top_k=top_k)
    if not scored:
        return FAQResult(MISS)

    best_score, best_entry = scored[0]
    logger.debug("FAQ best match scored %.3f", best_score)

    # Context is attached to every result, not just misses: a caller may decide
    # it needs the model anyway (the swim bot does, for live timetable
    # questions) and should still get the grounding.
    context = relevant_context(scored)

    if best_score >= settings.FAQ_MATCH_THRESHOLD:
        return FAQResult(
            MATCH, answer=best_entry["answer"], score=best_score, context=context
        )

    if best_score >= settings.FAQ_MIN_CONFIDENCE:
        return FAQResult(
            HEDGED,
            answer=HEDGE_PREFIX + best_entry["answer"],
            score=best_score,
            context=context,
        )

    return FAQResult(MISS, score=best_score, context=context)


def relevant_context(scored, limit=3):
    """FAQ answers worth putting in a prompt, best first.

    Anything below FAQ_CONTEXT_MIN_SCORE is dropped: a weak match is not
    background for the model, it's a distraction.
    """
    floor = settings.FAQ_CONTEXT_MIN_SCORE
    return [
        {"question": entry["question"], "answer": strip_tags(entry["answer"]).strip()}
        for score, entry in scored[:limit]
        if score >= floor
    ]


def format_context(context):
    """Render retrieved FAQs as a prompt block, or '' if there are none."""
    if not context:
        return ""
    lines = [f"- **{item['question']}** {item['answer']}" for item in context]
    return "\n".join(lines)
