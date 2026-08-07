"""Shared OpenAI plumbing for both chatbots: model choice, safe calls.

Every model and embedding call in the project goes through here so that the two
bots, the management commands and the admin action cannot drift apart on model
choice — which is exactly what happened before, with three settings files
declaring different defaults and views.py preferring os.getenv() over any of
them.
"""
import logging

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

_client = None

# Models that take the older completion parameters. Newer models reject
# max_tokens (they want max_completion_tokens) and reject any temperature other
# than the default, so the call has to be shaped per model.
LEGACY_PARAM_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-4-turbo"}

FRIENDLY_ERROR = (
    "Sorry — I can't answer right now. Please try again in a few minutes, or "
    "contact reception if it's urgent."
)


def get_client():
    """The shared OpenAI client, built on first use.

    Lazy so that importing this module doesn't reach into Django settings
    before they're configured, and so a missing key fails at call time with a
    handled error rather than at import time with a 500 on every page.
    """
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def chat_model():
    """The configured chat model (OPENAI_CHAT_MODEL in .env)."""
    return getattr(settings, "OPENAI_CHAT_MODEL", "gpt-5.4-mini")


def embed_model():
    """The configured embedding model (OPENAI_EMBED_MODEL in .env).

    Must stay in step with the model used to build FAQEntry.embedding — mixing
    the two produces plausible-looking similarity scores against vectors from a
    different space, which degrades matching without ever raising.
    """
    return getattr(settings, "OPENAI_EMBED_MODEL", "text-embedding-3-small")


def ask_openai(messages, *, max_tokens=600, temperature=0.3, timeout=20):
    """Call the chat model, returning (answer, error_message).

    Never raises: a provider outage, an expired key or an exhausted balance
    should show a customer a friendly note, not a 500 page or a raw traceback.
    """
    model = chat_model()
    kwargs = {"model": model, "messages": messages, "timeout": timeout}

    if model in LEGACY_PARAM_MODELS:
        kwargs["max_tokens"] = max_tokens
        kwargs["temperature"] = temperature
    else:
        kwargs["max_completion_tokens"] = max_tokens

    try:
        response = get_client().chat.completions.create(**kwargs)
        return response.choices[0].message.content, None
    except Exception as exc:
        logger.exception("Chat completion failed: %s", exc)
        return None, FRIENDLY_ERROR


def embed(text, *, timeout=15):
    """Embed a single string, or return None if the API is unavailable.

    Callers degrade to an unmatched query rather than failing the request.
    """
    try:
        response = get_client().embeddings.create(
            model=embed_model(),
            input=text,
            timeout=timeout,
        )
        return response.data[0].embedding
    except Exception as exc:
        logger.exception("Embedding failed: %s", exc)
        return None
