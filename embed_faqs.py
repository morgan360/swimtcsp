"""DEPRECATED — superseded by `manage.py rebuild_faq_embeddings`.

This script wrote embeddings built from the FAQ *question* alone, and pinned
both the settings module and the embedding model itself. FAQ vectors are now
built from question *and* answer (see chatbot.helpers.faq_index.embedding_text)
using the configured model, so running this would write vectors the matcher
cannot compare against — silently degrading every answer.

Use instead:

    python manage.py rebuild_faq_embeddings --force

which reads chatbot/data/faq.yaml, honours OPENAI_EMBED_MODEL, and works under
whichever settings module is active.
"""
import sys

sys.exit(
    "This script is deprecated. Run `python manage.py rebuild_faq_embeddings --force` instead."
)
