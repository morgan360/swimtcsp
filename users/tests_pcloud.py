from datetime import date, timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from users.management.commands import backup_to_pcloud as cmd

TODAY = date(2026, 11, 21)


def backup(day, fileid=None):
    return {"name": f"db_backup_{day:%d-%b-%Y}.sql.gz", "fileid": fileid or day.toordinal(), "isfolder": False}


def nightly(days):
    return [backup(TODAY - timedelta(days=n)) for n in range(days)]


class BackupsToDeleteTests(SimpleTestCase):
    def test_keeps_thirty_days(self):
        expired = cmd.backups_to_delete(nightly(40), TODAY)
        self.assertEqual([d for _, d in expired], [TODAY - timedelta(days=n) for n in range(39, 30, -1)])

    def test_never_touches_other_files(self):
        old = TODAY - timedelta(days=400)
        files = [
            {"name": "holiday-photos.jpg", "fileid": 1, "isfolder": False},
            {"name": "db_backup_01-Jan-2020.sql.zip", "fileid": 2, "isfolder": False},
            {"name": f"copy of db_backup_{old:%d-%b-%Y}.sql", "fileid": 3, "isfolder": False},
            {"name": f"db_backup_{old:%d-%b-%Y}.sql", "fileid": 4, "isfolder": True},
        ] + nightly(10)
        self.assertEqual(cmd.backups_to_delete(files, TODAY), [])

    def test_always_keeps_the_newest_few(self):
        # The task stopped for months: the last seven are kept even though old.
        stale = [backup(TODAY - timedelta(days=100 + n)) for n in range(10)]
        expired = cmd.backups_to_delete(stale, TODAY)
        self.assertEqual(len(expired), 3)
        self.assertEqual(expired[-1][1], TODAY - timedelta(days=107))

    def test_unparseable_dates_are_left_alone(self):
        files = [{"name": "db_backup_31-Feb-2020.sql", "fileid": 9, "isfolder": False}] + nightly(5)
        self.assertEqual(cmd.backups_to_delete(files, TODAY), [])


def fake_pcloud(listing, upload_result=0, folder_result=0):
    """Stand-ins for requests.get/post that record what was asked of pCloud."""
    calls = []

    def get(url, params=None, timeout=None):
        method = url.rsplit("/", 1)[1]
        calls.append((method, params))
        body = {"result": 0}
        if method == "createfolderifnotexists":
            body = {"result": folder_result, "error": "Log in required.", "metadata": {"folderid": 77}}
        elif method == "listfolder":
            body["metadata"] = {"contents": listing}
        return MagicMock(json=MagicMock(return_value=body))

    def post(url, params=None, files=None, timeout=None):
        calls.append(("uploadfile", {**params, "name": files["file"][0]}))
        return MagicMock(status_code=200, json=MagicMock(return_value={"result": upload_result, "error": "nope"}))

    return calls, get, post


def fake_mysqldump(size):
    def run(cmd, stdout=None, check=None, env=None):
        stdout.write("-- dump\n" + "x" * size)
    return run


@patch("users.management.commands.backup_to_pcloud.config", side_effect=lambda key, default=None: "token")
@patch("users.management.commands.backup_to_pcloud.date")
class CommandTests(SimpleTestCase):
    def run_command(self, mock_date, listing, *args, upload_result=0, folder_result=0, dump_size=200_000):
        mock_date.today.return_value = TODAY
        calls, get, post = fake_pcloud(listing, upload_result, folder_result)
        with patch("requests.get", side_effect=get), patch("requests.post", side_effect=post), \
                patch("subprocess.run", side_effect=fake_mysqldump(dump_size)) as run:
            out, err = StringIO(), StringIO()
            error = None
            try:
                call_command("backup_to_pcloud", *args, stdout=out, stderr=err)
            except CommandError as exc:
                error = str(exc)
        return calls, run, out.getvalue(), err.getvalue() + (error or "")

    def deleted(self, calls):
        return [params["fileid"] for method, params in calls if method == "deletefile"]

    def test_backs_up_the_live_database_then_deletes_expired(self, mock_date, _config):
        from django.conf import settings
        calls, run, out, _ = self.run_command(mock_date, nightly(35))
        cmd_line = run.call_args.args[0]
        self.assertEqual(cmd_line[-1], settings.DATABASES["default"]["NAME"])
        self.assertNotIn("-p", cmd_line)  # password not on the command line
        upload = next(params for method, params in calls if method == "uploadfile")
        self.assertEqual(upload["folderid"], 77)
        self.assertTrue(upload["name"].endswith(".sql.gz"))
        self.assertEqual(len(self.deleted(calls)), 4)
        self.assertIn("Deleted 4 backup(s)", out)

    def test_uses_its_own_folder(self, mock_date, _config):
        calls, _, _, _ = self.run_command(mock_date, nightly(3))
        folder = next(params for method, params in calls if method == "createfolderifnotexists")
        self.assertEqual(folder["path"], cmd.FOLDER)

    def test_failed_upload_deletes_nothing_and_fails_loudly(self, mock_date, _config):
        calls, _, _, err = self.run_command(mock_date, nightly(35), upload_result=2000)
        self.assertEqual(self.deleted(calls), [])
        self.assertIn("Upload failed", err)
        self.assertIn("no old backups were deleted", err)

    def test_empty_dump_is_not_uploaded(self, mock_date, _config):
        calls, _, _, err = self.run_command(mock_date, nightly(35), dump_size=0)
        self.assertFalse(any(method == "uploadfile" for method, _ in calls))
        self.assertEqual(self.deleted(calls), [])
        self.assertIn("bytes; not uploading", err)

    def test_expired_token_fails_loudly(self, mock_date, _config):
        calls, _, _, err = self.run_command(mock_date, nightly(35), folder_result=2000)
        self.assertIn("Make a new one", err)
        self.assertFalse(any(method == "uploadfile" for method, _ in calls))

    def test_dry_run_deletes_nothing(self, mock_date, _config):
        calls, run, out, _ = self.run_command(mock_date, nightly(35), "--prune-only", "--dry-run")
        self.assertFalse(run.called)
        self.assertEqual(self.deleted(calls), [])
        self.assertIn("Would delete 4 backup(s)", out)

    def test_nothing_left_in_tmp(self, mock_date, _config):
        import glob
        before = set(glob.glob("/tmp/db_backup_*"))
        self.run_command(mock_date, nightly(3))
        self.assertEqual(set(glob.glob("/tmp/db_backup_*")) - before, set())
