from chatbot.models import FAQEntry
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import logging

logger = logging.getLogger(__name__)

def match_faq(user_query, embed_func, lessons_mode=False, threshold=0.85):
    """
    Match a user query against FAQEntry model embeddings.

    Args:
        user_query (str): The user question.
        embed_func (callable): A function that returns an embedding vector.
        lessons_mode (bool): If True, only consider lesson-related FAQs.
        threshold (float): Cosine similarity threshold to return a match.

    Returns:
        Tuple[str or None, float]: The matched answer and its confidence score.
    """
    query_vector = embed_func(user_query)

    qs = FAQEntry.objects.filter(lessons_only=lessons_mode).exclude(embedding=None)
    faqs = list(qs)

    if not faqs:
        return None, 0.0

    scores = [
        cosine_similarity([query_vector], [faq.embedding])[0][0]
        for faq in faqs
    ]

    best_idx = int(np.argmax(scores))
    best_score = scores[best_idx]
    best_faq = faqs[best_idx]

    logger.info(f"🤖 FAQ match: '{user_query}' → '{best_faq.question}' (score: {best_score:.3f})")

    if best_score >= threshold:
        return best_faq.answer, best_score

    return None, best_score
