"""Confirm the moderation screen is actually working against the live API.

Worth its own command because the failure mode is silent by design. Screening
fails open — an OpenAI outage must not take the bot down for ordinary customers
— so a key that cannot reach /v1/moderations produces a warning in the log and
a bot that answers everything exactly as it did before. Nothing visibly breaks,
which is the worst way for a safety control to be switched off.

Run after any change to the API key or its permissions, and after deploying.

    python manage.py check_moderation --settings=config.production_settings

Exits non-zero if screening is not working, so it can gate a deploy step.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from chatbot.helpers import moderation

# Deliberately mild, and drawn from the July 2026 traffic rather than invented:
# enough to prove the endpoint classifies, without putting anything gratuitous
# in a command any staff member might run.
PROBE_ABUSIVE = "Can I sexually assault people in the shower"
PROBE_CLEAN = "What time is the next public swim?"


class Command(BaseCommand):
    help = "Verify that chatbot moderation is reachable and classifying."

    def handle(self, *args, **options):
        if not moderation.is_enabled():
            self.stdout.write(self.style.ERROR(
                "❌ CHATBOT_MODERATION_ENABLED is False — every message is "
                "passed through unscreened."
            ))
            raise SystemExit(1)

        self.stdout.write(f"Model: {moderation.MODERATION_MODEL}")

        abusive = moderation.check(PROBE_ABUSIVE)
        clean = moderation.check(PROBE_CLEAN)

        if not abusive.checked or not clean.checked:
            self.stdout.write(self.style.ERROR(
                "❌ The moderation endpoint could not be reached — see the log "
                "line above for the API error.\n"
                "   Screening is failing open: every message is currently "
                "reaching the FAQ and model tiers unscreened.\n"
                "   If the key is a restricted project key (sk-proj-...), it "
                "needs Moderations permission in the OpenAI dashboard."
            ))
            raise SystemExit(1)

        ok = True
        if abusive.flagged:
            self.stdout.write(self.style.SUCCESS(
                f"✅ Abusive probe flagged ({abusive.category_text})"
            ))
        else:
            ok = False
            self.stdout.write(self.style.ERROR(
                "❌ Abusive probe was NOT flagged — screening is reachable but "
                "not catching what it exists to catch."
            ))

        if clean.flagged:
            ok = False
            self.stdout.write(self.style.ERROR(
                f"❌ Ordinary question was flagged ({clean.category_text}) — "
                "real customers would be refused."
            ))
        else:
            self.stdout.write(self.style.SUCCESS("✅ Ordinary question passed"))

        recipients = getattr(settings, "CHATBOT_ABUSE_ALERT_EMAILS", "")
        if recipients:
            self.stdout.write(self.style.SUCCESS(f"✅ Alerts go to: {recipients}"))
        else:
            self.stdout.write(self.style.WARNING(
                "⚠️  CHATBOT_ABUSE_ALERT_EMAILS is empty — messages will be "
                "refused and recorded, but nobody will be told."
            ))

        if not ok:
            raise SystemExit(1)
        self.stdout.write(self.style.SUCCESS("Moderation is working."))