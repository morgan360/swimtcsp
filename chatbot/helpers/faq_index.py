"""In-memory FAQ vector index, rebuilt only when the FAQ set changes.

Matching used to re-fetch every FAQEntry and rebuild a float64 matrix on every
single message. The corpus changes a few times a year, so it is built once per
process and invalidated by a signal when an entry is saved or deleted.

Vectors are stored L2-normalised as float32, which makes cosine similarity a
single dot product and halves the resident matrix — no sklearn needed.
"""
import hashlib
import logging
import re
import threading
import uuid

import numpy as np
from django.core.cache import cache

from chatbot.models import FAQEntry

logger = logging.getLogger(__name__)

_VERSION_CACHE_KEY = "chatbot:faq_index_version"

_lock = threading.Lock()
_index = None
_index_version = None


def normalize(text):
    """Lowercased, whitespace-collapsed form used for exact-match lookups."""
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def embedding_text(question, answer=""):
    """The text an FAQ is embedded as: the question alone.

    Including the answer body was tried and measurably made things worse. Scored
    against 133 real historical questions, it compressed every score into
    0.55–0.72 and turned the one FAQ with a long, chatty answer ("Do you do
    Water safety training?", which names an external instructor and their email)
    into a hub that came top for unrelated queries. Questions are short and
    uniform, so question-only keeps unrelated traffic below 0.40 where it
    belongs.

    `answer` is accepted so callers need not care, and so the decision can be
    revisited in one place. Every writer of FAQEntry.embedding must use this —
    the management commands and the admin action previously each built their own
    input text.
    """
    return (question or "").strip()


def query_text(user_message):
    """The text a user question is embedded as: the question itself.

    An earlier version prefixed this with "Question about Templeogue College
    Swimming Pool:" to frame it. Because FAQs are embedded as bare questions,
    that made query and document asymmetric and dragged every score down —
    measured against production, "is there parking" scored 0.561 against the
    *identical* stored question, versus 0.900 unframed, and three of five test
    queries matched the wrong entry entirely.

    Both sides are now embedded the same way. Keep it that way: whatever is done
    here must also be done in embedding_text.
    """
    return user_message.strip()


# Bumped whenever the query embedding text changes, so cached vectors from the
# previous scheme are never compared against freshly embedded FAQs.
_QUERY_EMBED_VERSION = "v2-bare"


def query_cache_key(user_message):
    digest = hashlib.sha256(normalize(user_message).encode("utf-8")).hexdigest()
    return f"chatbot:qembed:{_QUERY_EMBED_VERSION}:{digest}"


def current_version():
    """The token identifying the current FAQ corpus.

    A random token rather than a counter: a cache flush would reset a counter
    to its starting value, and any process still holding an index stamped with
    that value would never notice it had gone stale.
    """
    version = cache.get(_VERSION_CACHE_KEY)
    if version is None:
        version = uuid.uuid4().hex
        cache.set(_VERSION_CACHE_KEY, version, None)
    return version


def invalidate():
    """Retire the current index so every process rebuilds on next use."""
    cache.set(_VERSION_CACHE_KEY, uuid.uuid4().hex, None)


class FAQIndex:
    """A snapshot of the FAQ corpus with its vectors ready to score."""

    def __init__(self, entries, matrix):
        self.entries = entries
        self.matrix = matrix
        self.by_question = {normalize(e["question"]): e for e in entries}

    def __len__(self):
        return len(self.entries)

    def exact_match(self, user_message, lessons_mode):
        """An entry whose question is textually identical, or None.

        Lets a repeated question skip the embedding call entirely.
        """
        entry = self.by_question.get(normalize(user_message))
        if entry and _visible(entry, lessons_mode):
            return entry
        return None

    def search(self, query_vector, lessons_mode, top_k=5):
        """Return [(score, entry)] best first, restricted to the bot's scope."""
        if self.matrix is None or not self.entries:
            return []

        vector = np.asarray(query_vector, dtype=np.float32)
        if vector.shape[0] != self.matrix.shape[1]:
            logger.warning(
                "Query vector is %d-d but the FAQ index is %d-d — the embedding "
                "model has changed; re-run `manage.py rebuild_faq_embeddings --force`.",
                vector.shape[0],
                self.matrix.shape[1],
            )
            return []

        norm = np.linalg.norm(vector)
        if not norm:
            return []
        scores = self.matrix @ (vector / norm)

        scored = [
            (float(scores[i]), entry)
            for i, entry in enumerate(self.entries)
            if _visible(entry, lessons_mode)
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return scored[:top_k]


def _visible(entry, lessons_mode):
    """Whether an entry is in scope for this bot.

    lessons_only entries belong to the lesson bot alone; everything else is
    shared. The old filter used exact equality on the flag, so the lesson bot
    saw *only* lessons_only rows — and since none were tagged, it matched
    nothing and paid for a model call on every message.
    """
    return lessons_mode or not entry["lessons_only"]


def _build():
    rows = list(
        FAQEntry.objects.exclude(embedding=None).values(
            "id", "question", "answer", "lessons_only", "embedding"
        )
    )
    if not rows:
        return FAQIndex([], None)

    # Mixed dimensions mean a partial re-embed with a different model. Keep the
    # majority and drop the rest rather than failing to answer anything at all.
    dims = {}
    for row in rows:
        dims[len(row["embedding"])] = dims.get(len(row["embedding"]), 0) + 1
    expected = max(dims, key=dims.get)
    if len(dims) > 1:
        logger.warning(
            "FAQ embeddings have mixed dimensions %s — keeping %d-d entries only. "
            "Run `manage.py rebuild_faq_embeddings --force`.",
            dims,
            expected,
        )

    entries, vectors = [], []
    for row in rows:
        if len(row["embedding"]) != expected:
            continue
        vector = np.asarray(row.pop("embedding"), dtype=np.float32)
        norm = np.linalg.norm(vector)
        if not norm or not np.isfinite(norm):
            continue
        vectors.append(vector / norm)
        entries.append(row)

    if not entries:
        return FAQIndex([], None)

    return FAQIndex(entries, np.vstack(vectors))


def get_index():
    """The current index, rebuilt only when the FAQ set has changed."""
    global _index, _index_version

    version = current_version()
    if _index is not None and _index_version == version:
        return _index

    with _lock:
        if _index is None or _index_version != version:
            _index = _build()
            _index_version = version
            logger.debug("Rebuilt FAQ index: %d entries (v%s)", len(_index), version)
    return _index
