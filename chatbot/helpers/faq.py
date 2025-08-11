import os
from chatbot.models import FAQEntry
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

# Read threshold from env; fall back to a safe default
FAQ_MATCH_THRESHOLD = float(os.getenv("FAQ_MATCH_THRESHOLD", "0.70"))

def match_faq(user_query, embed_func, lessons_mode=False, threshold=None, top_k=5):
    """
    Returns (answer_or_none, cosine_score)
    """
    if threshold is None:
        threshold = FAQ_MATCH_THRESHOLD

    query_vector = np.array(embed_func(user_query), dtype=np.float64)

    qs = FAQEntry.objects.filter(lessons_only=lessons_mode).exclude(embedding=None)
    faqs = list(qs)
    if not faqs:
        return None, 0.0

    faq_vecs = np.vstack([np.array(f.embedding, dtype=np.float64) for f in faqs])
    sims = cosine_similarity(query_vector.reshape(1, -1), faq_vecs)[0]

    best_idx = int(np.argmax(sims))
    best_score = float(sims[best_idx])
    best_faq = faqs[best_idx]

    # optional: quick debug of top-k
    if top_k and len(faqs) > 1:
        top_idx = np.argsort(-sims)[:min(top_k, len(faqs))]
        preview = [{"q": faqs[i].question, "score": float(sims[i])} for i in top_idx]
        logger.info("🔎 FAQ top matches for '%s': %s", user_query, preview)

    logger.info("🤖 FAQ best: '%s' → '%s' (cos=%.3f)", user_query, best_faq.question, best_score)

    if best_score >= threshold:
        return best_faq.answer, best_score
    return None, best_score
