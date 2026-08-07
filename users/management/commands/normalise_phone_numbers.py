"""
One-off repair of the legacy phone numbers on the User model.

Background
----------
`sync_users_from_remote` mapped the WordPress `billing_phone` meta key to
`other_phone`, so users imported from the old site have a blank `mobile_phone`
even though we hold a perfectly good number for them. Everything that reads a
guardian's phone (admin lists, class lists, school exports) looks at
`mobile_phone` only, so those numbers are invisible.

The numbers were also stored in whatever shape WordPress happened to hold them
("0851639462", "085 163 9462", "00353 85..."). `PHONENUMBER_DEFAULT_REGION` is
only set in local_settings, so on dev and production a bare national number has
no region to be parsed against and `PhoneNumberField.get_prep_value` falls back
to storing the raw string unchanged. That affects the numbers already sitting in
`mobile_phone` as well as the ones stranded in `other_phone`.

The command makes two passes:

  1. backfill  - users with a blank `mobile_phone` and a usable `other_phone`
                 get that number copied across, normalised.
  2. normalise - users who already have a `mobile_phone` keep it, but it is
                 rewritten in a consistent format.

An existing `mobile_phone` is never replaced by the `other_phone` value, and
`other_phone` itself is never modified or cleared -- it stays as the original
record of what was imported.

Every number written is valid E.164 (+353...). The command writes through
`Value(..., output_field=CharField())` rather than assigning to the field,
because `PhoneNumberField.get_prep_value` reformats using
`PHONENUMBER_DB_FORMAT` -- which is 'NATIONAL' in local_settings and unset (so
E.164) everywhere else. Going through the plain CharField keeps the result
identical in every environment instead of re-creating the original bug locally.

Numbers that cannot be parsed as a valid number are left exactly as they are and
listed in the report so they can be chased manually.

Usage
-----
    python manage.py normalise_phone_numbers                     # dry run, both passes
    python manage.py normalise_phone_numbers --commit
    python manage.py normalise_phone_numbers --report skipped.csv
"""

import csv
import re

import phonenumbers
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Case, CharField, Q, Value, When

from users.models import User

BATCH_SIZE = 500

# Keep digits and a leading '+'; drop spaces, brackets, dashes and stray text.
_NON_DIALLABLE = re.compile(r"[^0-9+]")


def normalise_irish(raw):
    """Return a raw phone string as valid E.164, or None if it isn't one.

    Numbers are assumed to be Irish, so bare national numbers are parsed against
    region IE. A number that already carries its own country code (+44...) keeps
    it -- the region only applies when there is nothing else to go on.
    """
    digits = _NON_DIALLABLE.sub("", raw or "")
    if not digits:
        return None

    # International prefix dialled the old way: 00353... -> +353...
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    # Country code present but unmarked: 353... -> +353...
    elif digits.startswith("353"):
        digits = "+" + digits
    # Country code followed by the national trunk '0': +3530xx -> +353xx
    if digits.startswith("+3530"):
        digits = "+353" + digits[5:]

    try:
        number = phonenumbers.parse(digits, "IE")
    except phonenumbers.NumberParseException:
        return None

    if not phonenumbers.is_valid_number(number):
        return None

    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


class Command(BaseCommand):
    help = "Recover legacy phone numbers into mobile_phone and store them as E.164."

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Write the changes. Without this the command only reports.",
        )
        parser.add_argument(
            "--report",
            metavar="PATH",
            help="Write the numbers that could not be parsed to this CSV.",
        )

    def handle(self, *args, **options):
        commit = options["commit"]

        backfill, backfill_skipped = self._collect_backfill()
        normalise, normalise_skipped = self._collect_normalise()

        self.stdout.write(self.style.MIGRATE_HEADING("Pass 1 — backfill from other_phone"))
        self.stdout.write(f"  blank mobile_phone with an other_phone : {len(backfill) + len(backfill_skipped)}")
        self.stdout.write(self.style.SUCCESS(f"  recoverable                           : {len(backfill)}"))
        self.stdout.write(self.style.WARNING(f"  unparseable, left alone               : {len(backfill_skipped)}"))

        self.stdout.write(self.style.MIGRATE_HEADING("Pass 2 — reformat existing mobile_phone"))
        self.stdout.write(f"  mobile_phone not already E.164        : {len(normalise) + len(normalise_skipped)}")
        self.stdout.write(self.style.SUCCESS(f"  reformattable                         : {len(normalise)}"))
        self.stdout.write(self.style.WARNING(f"  unparseable, left alone               : {len(normalise_skipped)}"))

        if options["report"]:
            with open(options["report"], "w", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(["pass", "id", "email", "value"])
                writer.writerows(("backfill", *row) for row in backfill_skipped)
                writer.writerows(("normalise", *row) for row in normalise_skipped)
            self.stdout.write(f"\nSkipped numbers written to {options['report']}")

        if not commit:
            self.stdout.write("")
            for pk, e164 in backfill[:5]:
                self.stdout.write(f"  backfill  user {pk} -> {e164}")
            for pk, e164 in normalise[:5]:
                self.stdout.write(f"  reformat  user {pk} -> {e164}")
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Dry run — nothing written. Re-run with --commit."))
            return

        total = 0
        with transaction.atomic():
            total += self._apply(backfill, "backfill")
            total += self._apply(normalise, "reformat")

        self.stdout.write(self.style.SUCCESS(f"✅ {total} phone numbers written as E.164."))

    def _collect_backfill(self):
        """Users with no mobile_phone whose other_phone can be recovered."""
        rows = (
            User.objects
            .filter(mobile_phone__in=["", None])
            .exclude(Q(other_phone__in=["", None]))
            .values_list("id", "email", "other_phone")
            .order_by("id")
        )
        return self._split(rows)

    def _collect_normalise(self):
        """Users who already have a mobile_phone that is not stored as E.164.

        `other_phone` is not consulted here -- an existing number is only ever
        reformatted, never replaced.
        """
        rows = (
            User.objects
            .exclude(mobile_phone__in=["", None])
            .exclude(mobile_phone__startswith="+")
            .values_list("id", "email", "mobile_phone")
            .order_by("id")
        )
        return self._split(rows)

    def _split(self, rows):
        """Sort rows into (pk, e164) updates and (pk, email, raw) skips."""
        updates, skipped = [], []
        for pk, email, raw in rows:
            e164 = normalise_irish(raw)
            if e164 and e164 != raw:
                updates.append((pk, e164))
            elif not e164:
                skipped.append((pk, email, raw))
        return updates, skipped

    def _apply(self, updates, label):
        written = 0
        for start in range(0, len(updates), BATCH_SIZE):
            batch = updates[start:start + BATCH_SIZE]
            User.objects.filter(pk__in=[pk for pk, _ in batch]).update(
                mobile_phone=Case(
                    *[
                        When(pk=pk, then=Value(e164, output_field=CharField()))
                        for pk, e164 in batch
                    ],
                    output_field=CharField(),
                )
            )
            written += len(batch)
            self.stdout.write(f"  {label} {written}/{len(updates)}")
        return written
