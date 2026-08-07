"""Startup checks for the chatbot's retrieval thresholds.

The three thresholds only make sense in a strict order. Production was found
holding FAQ_MATCH_THRESHOLD=0.40 while the code's hedge floor was 0.58 — which
silently makes the hedge tier unreachable and serves every weak match verbatim.
That is exactly the failure this catches, at startup rather than in front of a
customer.
"""
from django.conf import settings
from django.core.checks import Error, Warning, register


@register()
def check_faq_thresholds(app_configs, **kwargs):
    issues = []

    match = getattr(settings, "FAQ_MATCH_THRESHOLD", None)
    hedge = getattr(settings, "FAQ_MIN_CONFIDENCE", None)
    context = getattr(settings, "FAQ_CONTEXT_MIN_SCORE", None)

    named = {"FAQ_MATCH_THRESHOLD": match, "FAQ_MIN_CONFIDENCE": hedge,
             "FAQ_CONTEXT_MIN_SCORE": context}
    for name, value in named.items():
        if value is None:
            issues.append(Error(f"{name} is not configured.", id="chatbot.E001"))
        elif not 0.0 <= value <= 1.0:
            issues.append(Error(
                f"{name}={value} is outside the 0.0-1.0 range of a cosine score.",
                id="chatbot.E002",
            ))
    if issues:
        return issues

    if hedge > match:
        issues.append(Error(
            f"FAQ_MIN_CONFIDENCE ({hedge}) is above FAQ_MATCH_THRESHOLD ({match}), "
            f"so the hedged tier can never be reached and weak matches are served "
            f"verbatim.",
            hint="FAQ_CONTEXT_MIN_SCORE <= FAQ_MIN_CONFIDENCE <= FAQ_MATCH_THRESHOLD. "
                 "Check FAQ_MATCH_THRESHOLD in this environment's .env.",
            id="chatbot.E003",
        ))
    if context > hedge:
        issues.append(Error(
            f"FAQ_CONTEXT_MIN_SCORE ({context}) is above FAQ_MIN_CONFIDENCE ({hedge}), "
            f"so no FAQ can ever be used as prompt grounding.",
            id="chatbot.E004",
        ))

    # Calibrated against real traffic: genuine matches sat at 0.52-0.77 and
    # unrelated questions ("I can't login" at 0.504) below that.
    if match < 0.55:
        issues.append(Warning(
            f"FAQ_MATCH_THRESHOLD ({match}) is low enough to serve unrelated "
            f"questions a verbatim FAQ answer.",
            hint="Run `manage.py faq_calibrate` against this environment's traffic.",
            id="chatbot.W001",
        ))

    return issues
