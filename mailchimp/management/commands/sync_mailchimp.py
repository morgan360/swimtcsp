"""Copy opted-in customers to Mailchimp with up-to-date "TCSP: ..." tags.

Meant to run nightly as a PythonAnywhere scheduled task. Only accounts that
ticked "News by email" are touched. Anyone found unsubscribed in Mailchimp has
their tick-box turned off here, so the two never disagree for long.

Usage
-----
    python manage.py sync_mailchimp --dry-run   # what would be sent, no API calls
    python manage.py sync_mailchimp
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from mailchimp import services


class Command(BaseCommand):
    help = "Sync opted-in customers and their tags to the Mailchimp audience."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.filter(
            marketing_opt_in=True, is_active=True, archived_at__isnull=True, anonymised_at__isnull=True,
        ).only("id", "email", "first_name", "last_name")
        context = services.build_context()

        if options["dry_run"]:
            counts = {tag: 0 for tag in services.MANAGED_TAGS}
            total = 0
            for user in users:
                total += 1
                for tag, on in services.customer_tags(user, context).items():
                    counts[tag] += on
            self.stdout.write(f"{total} opted-in accounts would be synced.")
            for tag, n in counts.items():
                self.stdout.write(f"  {tag}: {n}")
            return

        if not services.is_configured():
            raise CommandError("MAILCHIMP_API_KEY / MAILCHIMP_LIST_ID are not set.")

        client = services.get_mailchimp_client()
        synced = opted_out = failed = 0
        for user in users.iterator(chunk_size=200):
            try:
                status = services.sync_user(user, context, client=client)
            except Exception as exc:  # noqa: BLE001 - keep going; report at the end
                failed += 1
                services.logger.warning("Mailchimp sync failed for user %s: %s", user.pk, services._error_text(exc))
                continue
            if status in ("unsubscribed", "cleaned"):
                services.record_opt_in(user, False, push=False)
                opted_out += 1
            else:
                synced += 1

        self.stdout.write(self.style.SUCCESS(
            f"Synced {synced}; {opted_out} had unsubscribed in Mailchimp and were turned off here; {failed} failed."))
