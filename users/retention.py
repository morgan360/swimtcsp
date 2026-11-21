"""How long customer data is kept, and what happens when that time is up.

Two stages, as proposed to Esther and Brian in the email of 7 November 2026
and agreed verbally; archiving unused imports was agreed with Morgan on 21 Nov:

1. **Archive** after ``ARCHIVE_AFTER`` (3 years) with no paid order, login or
   visit. Accounts brought over from the old WordPress site are archived sooner,
   ``LEGACY_GRACE`` (12 months) after the import, if they have never logged in
   or paid here: a full school year of booking windows has passed them by, and
   until then the import date was the only "activity" they had. The account stays: the parent can still log in, and their name, email
   and order history are untouched. What goes is the detail nobody needs for a
   family that has stopped coming: children's dates of birth, medical
   information and notes, the guardian's phone numbers and notes, and the
   login/visit/chatbot logs. Staff lists and search hide archived accounts
   unless asked. Logging in again clears ``archived_at``; the erased
   details are simply asked for again when they next book.

2. **Anonymise** after ``ANONYMISE_AFTER`` (6 years, the Revenue retention
   period for the payments) since the last paid order and last activity. Names
   and email are replaced, the account can no longer log in, and every swimmer
   on it is anonymised. Order rows are kept, so the accounts still add up.

A parent asking to be forgotten gets stage 2 straight away (``erase_user``),
however recent their orders.

Accounts are never deleted: ``Order.user`` and ``Swimling.guardian`` cascade,
so a delete would take the payment history with it. Staff accounts are never
touched.

Every change writes a ``DataRetentionEvent`` that names the fields cleared but
holds none of their values.
"""
from dataclasses import dataclass, field
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from users.models import ActiveDay, DataRetentionEvent, LoginEvent, Swimling

ARCHIVE_AFTER = timedelta(days=3 * 365)
ANONYMISE_AFTER = timedelta(days=6 * 365)
LEGACY_IMPORT_DATE = date(2025, 9, 13)  # bulk import from WordPress
LEGACY_GRACE = timedelta(days=365)

ANONYMOUS_NAME = "Erased"  # the word used in the email to Esther and Brian

User = get_user_model()


@dataclass
class Candidate:
    user: "User"
    last_activity: object  # datetime
    last_paid_order: object  # datetime or None


@dataclass
class Result:
    user_id: int
    action: str
    cleared: dict = field(default_factory=dict)


def _last_paid_orders():
    """Latest paid order per user across lessons, swims and schools: {user_id: datetime}."""
    from lessons_orders.models import Order as LessonOrder
    from schools_orders.models import Order as SchoolOrder
    from swims_orders.models import Order as SwimOrder

    latest = {}
    for model in (LessonOrder, SwimOrder, SchoolOrder):
        rows = model.objects.filter(paid=True).values("user_id").annotate(last=Max("created"))
        for row in rows:
            current = latest.get(row["user_id"])
            if current is None or row["last"] > current:
                latest[row["user_id"]] = row["last"]
    return latest


def _last_active_days():
    """Latest ActiveDay per user: {user_id: date}."""
    return dict(ActiveDay.objects.values("user_id").annotate(last=Max("date")).values_list("user_id", "last"))


def _aware(day):
    from datetime import datetime, time
    return timezone.make_aware(datetime.combine(day, time.min))


def customer_accounts():
    """Every account retention may act on: not staff, not an instructor."""
    return (
        User.objects.filter(is_staff=False, is_superuser=False, instructorprofile__isnull=True)
        .exclude(groups__name__in=["instructor", "assistant"])
    )


def find_candidates(now=None):
    """Accounts due for each stage: (to_archive, to_anonymise), lists of Candidate.

    Last activity is the latest of: paid order, login, a day on the site, and the
    date the account was made — so a new account nobody has used yet is not
    archived the day it turns three. The WordPress import is the exception: see
    is_dormant_import.
    """
    now = now or timezone.now()
    paid = _last_paid_orders()
    active = _last_active_days()

    to_archive, to_anonymise = [], []
    users = customer_accounts().filter(anonymised_at__isnull=True).only(
        "id", "email", "last_login", "date_joined", "archived_at")
    for user in users.iterator(chunk_size=500):
        moments = [user.date_joined, user.last_login, paid.get(user.id)]
        if user.id in active:
            moments.append(_aware(active[user.id]))
        last = max(m for m in moments if m is not None)
        candidate = Candidate(user=user, last_activity=last, last_paid_order=paid.get(user.id))
        if now - last >= ANONYMISE_AFTER:
            to_anonymise.append(candidate)
        elif user.archived_at is None and (
                now - last >= ARCHIVE_AFTER
                or is_dormant_import(user, paid.get(user.id), user.id in active, now)):
            to_archive.append(candidate)
    return to_archive, to_anonymise


def is_dormant_import(user, last_paid_order, has_visited, now):
    """Imported from WordPress and never used here, a year on."""
    return (
        timezone.localdate(user.date_joined, timezone.get_current_timezone()) == LEGACY_IMPORT_DATE
        and user.last_login is None
        and last_paid_order is None
        and not has_visited
        and now - user.date_joined >= LEGACY_GRACE
    )


def _clear(instance, fields):
    """Blank the given fields; return the names of those that held something."""
    cleared = []
    for name in fields:
        value = getattr(instance, name)
        if value not in (None, ""):
            model_field = instance._meta.get_field(name)
            setattr(instance, name, None if model_field.null else "")
            cleared.append(name)
    return cleared


def _delete_logs(user):
    from chatbot.models import ChatbotQuery

    counts = {
        "login_events": LoginEvent.objects.filter(user=user).delete()[0],
        "active_days": ActiveDay.objects.filter(user=user).delete()[0],
        "chatbot_queries": ChatbotQuery.objects.filter(user=user).delete()[0],
    }
    return {name: n for name, n in counts.items() if n}


@transaction.atomic
def archive_user(user, now=None, performed_by=None):
    """Stage 1. Erase the details a lapsed family no longer needs; keep the account."""
    now = now or timezone.now()
    user = User.objects.select_for_update().get(pk=user.pk)
    cleared = {}

    user_fields = _clear(user, ["mobile_phone", "other_phone", "admin_notes"])
    if user_fields:
        cleared["user"] = user_fields
    user.archived_at = now
    user.save(update_fields=["mobile_phone", "other_phone", "admin_notes", "archived_at"])

    swimling_fields = set()
    for swimling in Swimling.objects.filter(guardian=user):
        names = _clear(swimling, ["dob", "medical_info", "notes"])
        if names:
            swimling.save(update_fields=["dob", "medical_info", "notes"])
            swimling_fields.update(names)
    if swimling_fields:
        cleared["swimlings"] = sorted(swimling_fields)

    cleared.update(_delete_logs(user))

    # Only our nightly sync puts these tags on, and it only covers opted-in accounts.
    if user.marketing_opt_in and not _remove_from_mailchimp(user, permanently=False):
        cleared["mailchimp"] = "failed"

    DataRetentionEvent.objects.create(
        user_id=user.pk, action=DataRetentionEvent.ARCHIVED, detail=cleared,
        performed_by_id=getattr(performed_by, "pk", None))
    return Result(user.pk, DataRetentionEvent.ARCHIVED, cleared)


@transaction.atomic
def anonymise_user(user, now=None, performed_by=None, action=DataRetentionEvent.ANONYMISED):
    """Stage 2. Leave nothing that identifies the family; keep the order rows."""
    from allauth.account.models import EmailAddress
    from allauth.mfa.models import Authenticator
    from allauth.socialaccount.models import SocialAccount
    from progress.models import InstructorNote
    from waiting_list.models import WaitingList

    now = now or timezone.now()
    user = User.objects.select_for_update().get(pk=user.pk)
    if user.is_staff or user.is_superuser:
        raise ValueError("Staff accounts are never anonymised.")

    # Mailchimp first, while we still know the address.
    mailchimp_ok = _remove_from_mailchimp(user, permanently=True)

    user.first_name = ANONYMOUS_NAME
    user.last_name = ""
    user.username = None
    user.email = f"deleted-{user.pk}@anonymised.invalid"
    user.mobile_phone = ""
    user.other_phone = ""
    user.admin_notes = None
    user.marketing_opt_in = False
    user.marketing_opt_in_at = None
    user.is_active = False
    user.archived_at = user.archived_at or now
    user.anonymised_at = now
    user.set_unusable_password()  # also ends any open session
    user.save()

    swimlings = Swimling.objects.filter(guardian=user)
    swimling_ids = list(swimlings.values_list("id", flat=True))
    swimlings.update(first_name=ANONYMOUS_NAME, last_name="", dob=None, sco_role_num=None,
                     notes=None, medical_info=None)

    cleared = {
        "user": ["name", "email", "phones", "notes", "password"],
        "swimlings": len(swimling_ids),
        "email_addresses": EmailAddress.objects.filter(user=user).delete()[0],
        "social_accounts": SocialAccount.objects.filter(user=user).delete()[0],
        "authenticators": Authenticator.objects.filter(user=user).delete()[0],
        "instructor_notes": InstructorNote.objects.filter(swimling_id__in=swimling_ids).delete()[0],
        "waiting_list_notes": WaitingList.objects.filter(swimling_id__in=swimling_ids)
        .exclude(Q(notes__isnull=True) | Q(notes="")).update(notes=""),
    }
    cleared.update(_delete_logs(user))
    cleared = {k: v for k, v in cleared.items() if v}
    if not mailchimp_ok:
        cleared["mailchimp"] = "failed"

    DataRetentionEvent.objects.create(
        user_id=user.pk, action=action, detail=cleared, performed_by_id=getattr(performed_by, "pk", None))
    return Result(user.pk, action, cleared)


def erase_user(user, performed_by):
    """A parent's request to be forgotten: anonymise now, whatever the dates."""
    return anonymise_user(user, performed_by=performed_by, action=DataRetentionEvent.ERASED)


def unarchive_on_login(user):
    """A parent came back. Their erased details stay erased; the account is live again."""
    if user.archived_at is None or user.anonymised_at is not None:
        return False
    User.objects.filter(pk=user.pk).update(archived_at=None)
    user.archived_at = None
    DataRetentionEvent.objects.create(user_id=user.pk, action=DataRetentionEvent.UNARCHIVED)
    return True


def _remove_from_mailchimp(user, permanently):
    """Keep Mailchimp in step; True if it worked.

    A Mailchimp outage never stops the erasure here — the failure is recorded in
    the event's detail so it can be redone by hand.
    """
    from mailchimp import services
    try:
        if permanently:
            services.forget_member(user.email)
        else:
            services.clear_customer_tags(user.email)
    except Exception:  # noqa: BLE001 - logged inside services
        return False
    return True
