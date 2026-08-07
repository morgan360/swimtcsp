"""Report the confidence-score distribution of real chatbot traffic.

The retrieval thresholds were never calibrated — 0.65 in .env, 0.70 in the
matcher, 0.65 in the docs, all guesses. ChatbotQuery has recorded a score for
every message ever sent, so set them from this instead.
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from chatbot.models import ChatbotQuery

BANDS = [
    (0.90, 1.01), (0.80, 0.90), (0.70, 0.80), (0.65, 0.70),
    (0.60, 0.65), (0.55, 0.60), (0.50, 0.55), (0.45, 0.50),
    (0.40, 0.45), (0.00, 0.40),
]


class Command(BaseCommand):
    help = "Report FAQ match confidence distribution to calibrate the thresholds"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=365,
                            help="How far back to look (default: 365)")
        parser.add_argument("--source", help="Filter to one bot, e.g. public_swim")

    def handle(self, *args, **options):
        since = timezone.now() - timedelta(days=options["days"])
        qs = ChatbotQuery.objects.filter(timestamp__gte=since)
        if options["source"]:
            qs = qs.filter(source=options["source"])

        total = qs.count()
        if not total:
            self.stdout.write(self.style.WARNING("No chatbot queries in this period."))
            return

        self.stdout.write(self.style.SUCCESS(
            f"\n{total} queries since {since:%Y-%m-%d}"
        ))
        self.stdout.write(
            f"Thresholds in force — match: {settings.FAQ_MATCH_THRESHOLD} | "
            f"hedge: {settings.FAQ_MIN_CONFIDENCE} | "
            f"context floor: {settings.FAQ_CONTEXT_MIN_SCORE}\n"
        )

        self.stdout.write("Response type:")
        for row in qs.values("response_type").annotate(n=Count("id")).order_by("-n"):
            share = row["n"] / total * 100
            self.stdout.write(f"   {row['response_type'] or '(none)':<12} {row['n']:>6}  {share:5.1f}%")

        scored = qs.filter(confidence_score__isnull=False)
        scored_total = scored.count()
        self.stdout.write(f"\nScore distribution ({scored_total} scored):")
        for low, high in BANDS:
            n = scored.filter(confidence_score__gte=low, confidence_score__lt=high).count()
            if not n:
                continue
            share = n / scored_total * 100
            bar = "█" * int(share / 2)
            self.stdout.write(f"   {low:.2f}–{high:.2f}  {n:>6}  {share:5.1f}%  {bar}")

        # The band that decides whether lowering the match threshold is safe.
        near = scored.filter(
            confidence_score__gte=settings.FAQ_MIN_CONFIDENCE,
            confidence_score__lt=settings.FAQ_MATCH_THRESHOLD,
        ).order_by("-confidence_score")
        self.stdout.write(self.style.WARNING(
            f"\nNear misses ({near.count()}) — served hedged, or sent to the model "
            f"before the tiering change. Each is a candidate for a new FAQ or a "
            f"reworded existing one:"
        ))
        for q in near[:25]:
            self.stdout.write(f"   {q.confidence_score:.3f}  {q.message[:70]}")

        # Repeat questions are the ones worth having as verbatim FAQ entries.
        self.stdout.write(self.style.WARNING("\nMost frequent questions:"))
        top = qs.values("message").annotate(n=Count("id")).order_by("-n")[:20]
        for row in top:
            if row["n"] < 2:
                break
            self.stdout.write(f"   {row['n']:>4}×  {row['message'][:70]}")

        self.stdout.write("")
