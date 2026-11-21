from datetime import date, timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from lessons_orders.models import Order as LessonOrder
from users import retention
from users.models import ActiveDay, DataRetentionEvent, LoginEvent, Swimling

User = get_user_model()

MAILCHIMP = {"MAILCHIMP_API_KEY": "key-us1", "MAILCHIMP_LIST_ID": "list"}


def years_ago(n):
    return timezone.now() - timedelta(days=int(n * 365) + 2)


class RetentionTestCase(TestCase):
    def make_customer(self, email, last_seen_years, paid_years=None):
        user = User.objects.create_user(email=email, password="pw-123456!", first_name="Ann", last_name="Byrne",
                                        mobile_phone="+353851234567", admin_notes="prefers evenings")
        User.objects.filter(pk=user.pk).update(date_joined=years_ago(last_seen_years),
                                               last_login=years_ago(last_seen_years))
        if paid_years is not None:
            order = LessonOrder.objects.create(user=user, paid=True, amount=100)
            LessonOrder.objects.filter(pk=order.pk).update(created=years_ago(paid_years))
        Swimling.objects.create(guardian=user, first_name="Cara", last_name="Byrne", dob=date(2015, 5, 1),
                                medical_info="asthma", notes="nervous in deep water")
        user.refresh_from_db()
        return user


@patch("mailchimp.services.get_mailchimp_client")
class FindCandidatesTests(RetentionTestCase):
    def test_sorts_accounts_by_how_long_they_have_been_quiet(self, _client):
        recent = self.make_customer("recent@example.com", 1, paid_years=1)
        lapsed = self.make_customer("lapsed@example.com", 4, paid_years=4)
        gone = self.make_customer("gone@example.com", 7, paid_years=7)

        to_archive, to_anonymise = retention.find_candidates()

        self.assertEqual([c.user.pk for c in to_archive], [lapsed.pk])
        self.assertEqual([c.user.pk for c in to_anonymise], [gone.pk])
        self.assertNotIn(recent.pk, [c.user.pk for c in to_archive + to_anonymise])

    def test_three_years_is_the_line(self, _client):
        self.make_customer("two@example.com", 2.5)
        user = self.make_customer("three@example.com", 3.1)
        self.assertEqual([c.user.pk for c in retention.find_candidates()[0]], [user.pk])

    def test_unused_import_is_archived_after_a_year(self, _client):
        user = self.make_customer("imported@example.com", 0)
        User.objects.filter(pk=user.pk).update(date_joined=self.import_moment(), last_login=None)
        now = self.import_moment() + timedelta(days=366)
        self.assertEqual([c.user.pk for c in retention.find_candidates(now)[0]], [user.pk])
        self.assertEqual(retention.find_candidates(now - timedelta(days=2)), ([], []))

    def test_import_that_logged_in_or_paid_is_left_alone(self, _client):
        logged_in = self.make_customer("came-back@example.com", 0)
        paid = self.make_customer("paid@example.com", 0, paid_years=1.5)
        moment = self.import_moment()
        User.objects.filter(pk=logged_in.pk).update(date_joined=moment, last_login=moment + timedelta(days=30))
        User.objects.filter(pk=paid.pk).update(date_joined=moment, last_login=None)
        now = moment + timedelta(days=400)
        self.assertEqual(retention.find_candidates(now), ([], []))

    def test_other_signups_are_not_treated_as_imports(self, _client):
        user = self.make_customer("new@example.com", 0)
        User.objects.filter(pk=user.pk).update(date_joined=self.import_moment() + timedelta(days=1), last_login=None)
        now = self.import_moment() + timedelta(days=400)
        self.assertEqual(retention.find_candidates(now), ([], []))

    @staticmethod
    def import_moment():
        from datetime import datetime, time
        return timezone.make_aware(datetime.combine(retention.LEGACY_IMPORT_DATE, time(12)))

    def test_a_recent_order_keeps_an_account_current(self, _client):
        user = self.make_customer("buyer@example.com", 5, paid_years=1)
        self.assertEqual(retention.find_candidates(), ([], []))
        self.assertIsNone(user.archived_at)

    def test_a_recent_visit_keeps_an_account_current(self, _client):
        user = self.make_customer("visitor@example.com", 5)
        ActiveDay.objects.create(user=user, date=timezone.localdate() - timedelta(days=30))
        self.assertEqual(retention.find_candidates(), ([], []))

    def test_staff_are_never_candidates(self, _client):
        user = self.make_customer("staff@example.com", 8)
        User.objects.filter(pk=user.pk).update(is_staff=True)
        self.assertEqual(retention.find_candidates(), ([], []))

    def test_already_archived_accounts_are_not_archived_again(self, _client):
        user = self.make_customer("lapsed@example.com", 4)
        retention.archive_user(user)
        self.assertEqual(retention.find_candidates(), ([], []))


@patch("mailchimp.services.get_mailchimp_client")
class ArchiveTests(RetentionTestCase):
    def test_erases_details_but_keeps_the_account(self, _client):
        user = self.make_customer("lapsed@example.com", 4, paid_years=4)
        LoginEvent.objects.create(user=user)
        ActiveDay.objects.create(user=user, date=date(2022, 1, 1))

        result = retention.archive_user(user)

        user.refresh_from_db()
        swimling = user.swimling_set.get()
        self.assertIsNotNone(user.archived_at)
        self.assertTrue(user.is_active)
        self.assertEqual((user.first_name, user.email), ("Ann", "lapsed@example.com"))
        self.assertEqual(str(user.mobile_phone), "")
        self.assertIsNone(user.admin_notes)
        self.assertEqual(swimling.first_name, "Cara")
        self.assertIsNone(swimling.dob)
        self.assertIsNone(swimling.medical_info)
        self.assertIsNone(swimling.notes)
        self.assertFalse(LoginEvent.objects.filter(user=user).exists())
        self.assertFalse(ActiveDay.objects.filter(user=user).exists())
        self.assertEqual(LessonOrder.objects.filter(user=user).count(), 1)
        self.assertEqual(result.cleared["swimlings"], ["dob", "medical_info", "notes"])

    def test_audit_event_holds_no_personal_details(self, _client):
        user = self.make_customer("lapsed@example.com", 4)
        retention.archive_user(user)
        event = DataRetentionEvent.objects.get(user_id=user.pk)
        self.assertEqual(event.action, DataRetentionEvent.ARCHIVED)
        for value in ("lapsed@example.com", "Ann", "asthma", "851234567"):
            self.assertNotIn(value, str(event.detail))

    def test_logging_in_again_unarchives(self, _client):
        user = self.make_customer("lapsed@example.com", 4)
        retention.archive_user(user)
        self.client.login(email="lapsed@example.com", password="pw-123456!")
        user.refresh_from_db()
        self.assertIsNone(user.archived_at)
        self.assertTrue(DataRetentionEvent.objects.filter(user_id=user.pk, action="unarchived").exists())

    def test_staff_hijacking_in_does_not_unarchive(self, _client):
        user = self.make_customer("lapsed@example.com", 4)
        retention.archive_user(user)
        from django.contrib.auth.signals import user_logged_in
        from django.test import RequestFactory
        from django.urls import reverse
        request = RequestFactory().post(reverse("hijack:acquire"))
        user_logged_in.send(sender=User, request=request, user=user)
        user.refresh_from_db()
        self.assertIsNotNone(user.archived_at)


@override_settings(**MAILCHIMP)
@patch("mailchimp.services.get_mailchimp_client")
class AnonymiseTests(RetentionTestCase):
    def test_leaves_nothing_identifying_and_keeps_orders(self, get_client):
        user = self.make_customer("gone@example.com", 7, paid_years=7)

        retention.anonymise_user(user)

        user.refresh_from_db()
        swimling = user.swimling_set.get()
        self.assertEqual(user.first_name, retention.ANONYMOUS_NAME)
        self.assertEqual(user.email, f"deleted-{user.pk}@anonymised.invalid")
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())
        self.assertIsNotNone(user.anonymised_at)
        self.assertEqual((swimling.first_name, swimling.last_name, swimling.dob), (retention.ANONYMOUS_NAME, "", None))
        self.assertEqual(LessonOrder.objects.filter(user=user).count(), 1)
        get_client.return_value.lists.delete_list_member_permanent.assert_called_once()

    def test_erasure_on_request_ignores_dates(self, _client):
        user = self.make_customer("recent@example.com", 0, paid_years=0)
        staff = User.objects.create_superuser(email="boss@example.com", password="x", first_name="B")
        retention.erase_user(user, performed_by=staff)
        event = DataRetentionEvent.objects.get(user_id=user.pk)
        self.assertEqual((event.action, event.performed_by_id), (DataRetentionEvent.ERASED, staff.pk))

    def test_mailchimp_outage_does_not_stop_erasure(self, get_client):
        get_client.return_value.lists.delete_list_member_permanent.side_effect = Exception("down")
        user = self.make_customer("gone@example.com", 7)
        result = retention.anonymise_user(user)
        user.refresh_from_db()
        self.assertIsNotNone(user.anonymised_at)
        self.assertEqual(result.cleared["mailchimp"], "failed")

    def test_refuses_staff(self, _client):
        user = self.make_customer("staff@example.com", 8)
        User.objects.filter(pk=user.pk).update(is_staff=True)
        with self.assertRaises(ValueError):
            retention.anonymise_user(user)


@patch("mailchimp.services.get_mailchimp_client")
class CommandTests(RetentionTestCase):
    def test_dry_run_changes_nothing(self, _client):
        user = self.make_customer("lapsed@example.com", 4)
        out = StringIO()
        call_command("apply_data_retention", stdout=out)
        user.refresh_from_db()
        self.assertIsNone(user.archived_at)
        self.assertIn("Due for archiving (3+ years inactive, or unused import): 1", out.getvalue())
        self.assertIn("Dry run", out.getvalue())

    def test_commit_archives_and_anonymises(self, _client):
        lapsed = self.make_customer("lapsed@example.com", 4)
        gone = self.make_customer("gone@example.com", 7)
        call_command("apply_data_retention", "--commit", stdout=StringIO())
        lapsed.refresh_from_db()
        gone.refresh_from_db()
        self.assertIsNotNone(lapsed.archived_at)
        self.assertIsNone(lapsed.anonymised_at)
        self.assertIsNotNone(gone.anonymised_at)

    def test_report_holds_ids_not_emails(self, _client):
        import os
        import tempfile
        self.make_customer("lapsed@example.com", 4)
        path = os.path.join(tempfile.mkdtemp(), "due.csv")
        call_command("apply_data_retention", "--report", path, stdout=StringIO())
        with open(path) as fh:
            text = fh.read()
        self.assertIn("archive", text)
        self.assertNotIn("lapsed@example.com", text)


@patch("mailchimp.services.get_mailchimp_client")
class EraseActionTests(RetentionTestCase):
    def setUp(self):
        from django.urls import reverse
        self.url = reverse("settings:users_user_changelist")
        self.customer = self.make_customer("parent@example.com", 0)

    def post(self, user, **extra):
        self.client.force_login(user)
        return self.client.post(self.url, {"action": "erase_personal_data",
                                           "_selected_action": [self.customer.pk], **extra})

    def test_asks_for_confirmation_first(self, _client):
        boss = User.objects.create_superuser(email="boss@example.com", password="x", first_name="B")
        response = self.post(boss)
        self.assertContains(response, "This cannot be undone")
        self.customer.refresh_from_db()
        self.assertIsNone(self.customer.anonymised_at)

    def test_confirmed_erases(self, _client):
        boss = User.objects.create_superuser(email="boss@example.com", password="x", first_name="B")
        self.post(boss, confirm_erase="yes")
        self.customer.refresh_from_db()
        self.assertIsNotNone(self.customer.anonymised_at)

    def test_ordinary_staff_cannot_erase(self, _client):
        from django.contrib.auth.models import Permission
        clerk = User.objects.create_user(email="clerk@example.com", password="x", first_name="C")
        User.objects.filter(pk=clerk.pk).update(is_staff=True)
        clerk.refresh_from_db()
        clerk.user_permissions.add(*Permission.objects.filter(codename__in=["view_user", "change_user"]))
        self.post(clerk, confirm_erase="yes")
        self.customer.refresh_from_db()
        self.assertIsNone(self.customer.anonymised_at)


@patch("mailchimp.services.get_mailchimp_client")
class HiddenWhenArchivedTests(RetentionTestCase):
    """The email to Esther and Brian promised archived families are hidden by default."""

    def setUp(self):
        self.boss = User.objects.create_superuser(email="boss@example.com", password="x", first_name="B")
        self.archived = self.make_customer("lapsed@example.com", 4)
        User.objects.filter(pk=self.archived.pk).update(last_name="Quigley")
        self.archived.refresh_from_db()
        with patch("mailchimp.services.get_mailchimp_client"):
            retention.archive_user(self.archived)
        self.client.force_login(self.boss)

    def search(self, **params):
        from django.urls import reverse
        return self.client.get(reverse("operations:tcsp_search"), {"q": "Quigley", **params})

    def test_search_hides_archived_unless_ticked(self, _client):
        self.assertEqual(self.search().context["guardian_total"], 0)
        response = self.search(archived="1")
        self.assertEqual(response.context["guardian_total"], 1)
        self.assertContains(response, "(archived)")

    def test_guardian_list_hides_archived_by_default(self, _client):
        from django.urls import reverse
        url = reverse("operations:users_user_changelist")
        self.assertNotContains(self.client.get(url, {"q": "Quigley"}), "lapsed@example.com")
        self.assertContains(self.client.get(url, {"q": "Quigley", "retention": "archived"}), "lapsed@example.com")

    def test_anonymised_children_are_named_erased(self, _client):
        retention.anonymise_user(self.archived)
        self.assertEqual(self.archived.swimling_set.get().first_name, "Erased")
