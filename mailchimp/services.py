"""Keeping the Mailchimp audience in step with the booking site.

Who goes to Mailchimp: only accounts that ticked "News by email"
(``User.marketing_opt_in``), plus anyone using the homepage newsletter box.
Customers who never agreed are never copied across.

What they carry: tags that describe them as customers, so Esther can send to
"booked this term" or "didn't rebook" without exporting spreadsheets. Every
tag this code manages starts with ``TAG_PREFIX``; tags anyone adds by hand in
Mailchimp are left alone.

Unsubscribes win. A member who unsubscribes in Mailchimp is never resubscribed
by the sync; instead their tick-box here is turned off to match.
"""
import hashlib
import logging

from django.conf import settings
from django.utils import timezone

from .client import get_mailchimp_client

logger = logging.getLogger("mailchimp")

TAG_PREFIX = "TCSP: "
TAG_CUSTOMER = TAG_PREFIX + "Customer"
TAG_BOOKED = TAG_PREFIX + "Lessons booked"
TAG_NOT_REBOOKED = TAG_PREFIX + "Lessons not rebooked"
TAG_WAITING = TAG_PREFIX + "Waiting list"
TAG_PUBLIC_SWIM = TAG_PREFIX + "Public swims"
MANAGED_TAGS = [TAG_CUSTOMER, TAG_BOOKED, TAG_NOT_REBOOKED, TAG_WAITING, TAG_PUBLIC_SWIM]

NEWSLETTER_TAG = "Newsletter"


def member_hash(email):
    return hashlib.md5(email.strip().lower().encode()).hexdigest()


def is_configured():
    return bool(getattr(settings, "MAILCHIMP_API_KEY", "") and getattr(settings, "MAILCHIMP_LIST_ID", ""))


def _error_status(exc):
    return getattr(exc, "status", None) or getattr(exc, "status_code", None)


def _error_text(exc):
    return getattr(exc, "text", "") or str(exc)


def subscribe(email, first_name="", last_name="", tags=()):
    """Add or update a member who has just agreed to receive news.

    This is a fresh, explicit opt-in, so a previously unsubscribed member is
    asked to confirm by email ("pending"): Mailchimp refuses a straight
    resubscribe for them, and is right to.
    """
    client = get_mailchimp_client()
    list_id = settings.MAILCHIMP_LIST_ID
    h = member_hash(email)
    body = {
        "email_address": email,
        "status_if_new": "subscribed",
        "merge_fields": {"FNAME": first_name or "", "LNAME": last_name or ""},
    }
    member = client.lists.set_list_member(list_id, h, body)
    if member.get("status") in ("unsubscribed", "archived"):
        member = client.lists.set_list_member(list_id, h, {**body, "status": "pending"})
    if tags:
        client.lists.update_list_member_tags(
            list_id, h, {"tags": [{"name": t, "status": "active"} for t in tags]})
    return member


def unsubscribe(email):
    """The parent unticked the box on their profile."""
    client = get_mailchimp_client()
    try:
        client.lists.update_list_member(settings.MAILCHIMP_LIST_ID, member_hash(email), {"status": "unsubscribed"})
    except Exception as exc:  # noqa: BLE001
        if _error_status(exc) != 404:
            raise


def customer_tags(user, context):
    """The managed tags this account should carry now: {tag: bool}."""
    uid = user.pk
    return {
        TAG_CUSTOMER: uid in context["paid_users"],
        TAG_BOOKED: uid in context["booked_users"],
        TAG_NOT_REBOOKED: uid in context["lapsed_users"] and uid not in context["booked_users"],
        TAG_WAITING: uid in context["waiting_users"],
        TAG_PUBLIC_SWIM: uid in context["swim_users"],
    }


def build_context(now=None):
    """Look up, once for the whole sync, which accounts belong under each tag."""
    from datetime import timedelta

    from lessons_bookings.models import LessonEnrollment, Term
    from lessons_orders.models import Order as LessonOrder
    from schools_orders.models import Order as SchoolOrder
    from swims_orders.models import Order as SwimOrder
    from waiting_list.models import WaitingList

    now = now or timezone.now()

    paid_users = set()
    for model in (LessonOrder, SwimOrder, SchoolOrder):
        paid_users.update(model.objects.filter(paid=True).values_list("user_id", flat=True).distinct())

    # Between terms, "booked" means booked for the coming one.
    upcoming = [t for t in (Term.get_current_term(), Term.get_next_term()) if t]
    previous = Term.get_previous_term()

    def guardians_enrolled(terms):
        if not terms:
            return set()
        return set(LessonEnrollment.objects.filter(term__in=terms)
                   .values_list("swimling__guardian_id", flat=True).distinct())

    booked_users = guardians_enrolled(upcoming)
    lapsed_users = guardians_enrolled([previous] if previous else [])

    waiting_users = set(WaitingList.objects.filter(completed=False)
                        .values_list("swimling__guardian_id", flat=True).distinct())
    swim_users = set(SwimOrder.objects.filter(paid=True, created__gte=now - timedelta(days=365))
                     .values_list("user_id", flat=True).distinct())

    return {
        "paid_users": paid_users,
        "booked_users": booked_users,
        "lapsed_users": lapsed_users,
        "waiting_users": waiting_users,
        "swim_users": swim_users,
    }


def sync_user(user, context, client=None):
    """Bring one opted-in account's Mailchimp record up to date.

    Returns the member's Mailchimp status. If they have unsubscribed there, the
    caller turns their opt-in off rather than pushing them back in.
    """
    client = client or get_mailchimp_client()
    list_id = settings.MAILCHIMP_LIST_ID
    h = member_hash(user.email)
    member = client.lists.set_list_member(list_id, h, {
        "email_address": user.email,
        "status_if_new": "subscribed",
        "merge_fields": {"FNAME": user.first_name or "", "LNAME": user.last_name or ""},
    })
    status = member.get("status")
    if status == "subscribed":
        wanted = customer_tags(user, context)
        client.lists.update_list_member_tags(list_id, h, {"tags": [
            {"name": tag, "status": "active" if on else "inactive"} for tag, on in wanted.items()
        ]})
    return status


def clear_customer_tags(email):
    """Archived account: they are no longer a current customer, so drop our tags.

    Their newsletter subscription is their own choice and is left as it is.
    """
    if not is_configured():
        return
    client = get_mailchimp_client()
    try:
        client.lists.update_list_member_tags(settings.MAILCHIMP_LIST_ID, member_hash(email), {
            "tags": [{"name": t, "status": "inactive"} for t in MANAGED_TAGS]})
    except Exception as exc:  # noqa: BLE001
        if _error_status(exc) != 404:
            logger.warning("Mailchimp: could not clear tags for user being archived: %s", _error_text(exc))
            raise


def forget_member(email):
    """Anonymised or erased account: remove the contact from Mailchimp for good.

    A permanent delete, not an archive — an archived Mailchimp contact still
    holds the address. Mailchimp lets the person sign up again later if they wish.
    """
    if not is_configured():
        return
    client = get_mailchimp_client()
    try:
        client.lists.delete_list_member_permanent(settings.MAILCHIMP_LIST_ID, member_hash(email))
    except Exception as exc:  # noqa: BLE001
        if _error_status(exc) != 404:
            logger.warning("Mailchimp: could not delete contact of erased user: %s", _error_text(exc))
            raise


def record_opt_in(user, agreed, push=True):
    """Store the parent's choice from a tick-box, and tell Mailchimp straight away.

    Mailchimp being down must not stop a sign-up or a profile save; the nightly
    sync catches up.
    """
    if bool(user.marketing_opt_in) == bool(agreed):
        return
    from django.contrib.auth import get_user_model
    user.marketing_opt_in = bool(agreed)
    user.marketing_opt_in_at = timezone.now() if agreed else None
    get_user_model().objects.filter(pk=user.pk).update(
        marketing_opt_in=user.marketing_opt_in, marketing_opt_in_at=user.marketing_opt_in_at)
    if not (push and is_configured()):
        return
    try:
        if agreed:
            subscribe(user.email, user.first_name, user.last_name)
        else:
            unsubscribe(user.email)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Mailchimp: could not record opt-%s for user %s: %s",
                       "in" if agreed else "out", user.pk, _error_text(exc))

