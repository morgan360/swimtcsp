"""Archive customers inactive for 3 years and anonymise those inactive for 6.

Unused accounts from the 2025 WordPress import are archived a year after it.

See users/retention.py for exactly what each stage removes and keeps.

A dry run by default: it counts and lists, and changes nothing. Nothing in it
is reversible once committed, so look at the dry run first.

Usage
-----
    python manage.py apply_data_retention                       # dry run, both stages
    python manage.py apply_data_retention --report due.csv      # dry run + list of account ids
    python manage.py apply_data_retention --stage archive --commit
    python manage.py apply_data_retention --commit --limit 200  # do it in batches

Before the first --commit on production, take a database backup (as promised
to Esther and Brian), and delete it after 30 days so the erased details do not
live on in it.

The report holds account ids and dates only — never names or contact details —
so it is safe to keep.
"""
import csv

from django.core.management.base import BaseCommand
from django.utils import timezone

from users import retention


class Command(BaseCommand):
    help = "Archive customers inactive for 3 years; anonymise those inactive for 6. Dry run unless --commit."

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true", help="Make the changes. Without it, nothing is written.")
        parser.add_argument("--stage", choices=["archive", "anonymise", "both"], default="both")
        parser.add_argument("--limit", type=int, default=0, help="At most this many accounts per stage.")
        parser.add_argument("--report", help="Write the accounts due to this CSV (ids and dates only).")

    def handle(self, *args, **options):
        now = timezone.now()
        to_archive, to_anonymise = retention.find_candidates(now)
        stage = options["stage"]
        if stage == "archive":
            to_anonymise = []
        elif stage == "anonymise":
            to_archive = []
        if options["limit"]:
            to_archive = to_archive[:options["limit"]]
            to_anonymise = to_anonymise[:options["limit"]]

        self.stdout.write(f"Due for archiving (3+ years inactive, or unused import): {len(to_archive)}")
        self.stdout.write(f"Due for anonymising (6+ years inactive): {len(to_anonymise)}")

        if options["report"]:
            with open(options["report"], "w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["user_id", "stage", "last_activity", "last_paid_order"])
                for name, group in (("archive", to_archive), ("anonymise", to_anonymise)):
                    for c in group:
                        writer.writerow([c.user.pk, name, c.last_activity.date().isoformat(),
                                         c.last_paid_order.date().isoformat() if c.last_paid_order else ""])
            self.stdout.write(f"Report written to {options['report']}")

        if not options["commit"]:
            self.stdout.write(self.style.WARNING("Dry run: nothing changed. Add --commit to apply."))
            return

        failures = 0
        done = {"archived": 0, "anonymised": 0}
        for c in to_archive:
            try:
                retention.archive_user(c.user, now=now)
                done["archived"] += 1
            except Exception as exc:  # noqa: BLE001 - one bad account must not stop the rest
                failures += 1
                self.stderr.write(f"User {c.user.pk}: archive failed: {exc}")
        for c in to_anonymise:
            try:
                retention.anonymise_user(c.user, now=now)
                done["anonymised"] += 1
            except Exception as exc:  # noqa: BLE001
                failures += 1
                self.stderr.write(f"User {c.user.pk}: anonymise failed: {exc}")

        self.stdout.write(self.style.SUCCESS(
            f"Archived {done['archived']}, anonymised {done['anonymised']}, failed {failures}."))
