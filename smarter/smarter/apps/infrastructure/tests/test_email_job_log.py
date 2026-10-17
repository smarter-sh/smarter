"""
Test manage.py email_job_log.

No email is sent: the tests use the in-memory email service. Nothing is saved to S3: the
default file storage is replaced with an in-memory one.
"""

import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.files.storage import InMemoryStorage
from django.core.management import call_command

from smarter.apps.infrastructure.management.commands.email_job_log import (
    REDACTED,
    STORAGE_FOLDER,
    redact,
    save_public,
    secret_values,
)
from smarter.apps.infrastructure.services import InMemoryEmailService, configure_email
from smarter.common.conf import smarter_settings

from .base import InfrastructureTestBase

MODULE = "smarter.apps.infrastructure.management.commands.email_job_log"


class TestRedact(InfrastructureTestBase):
    """Test redact() and secret_values()."""

    def test_redacts_credentials(self):
        env = {"SMARTER_MYSQL_PASSWORD": "hunter2-long", "SOME_API_KEY": "sk-abcdef", "SMARTER_MYSQL_PORT": "3306306"}
        with patch.dict(os.environ, env):
            self.assertIn("hunter2-long", secret_values())
            self.assertNotIn("3306306", secret_values())
            text = redact("password hunter2-long, key sk-abcdef, port 3306306")
        self.assertEqual(text, f"password {REDACTED}, key {REDACTED}, port 3306306")

    def test_short_values_are_not_redacted(self):
        with patch.dict(os.environ, {"SMARTER_TOKEN": "abc"}):
            self.assertEqual(redact("abc"), "abc")


class TestSavePublic(InfrastructureTestBase):
    """Test save_public()."""

    def setUp(self):
        super().setUp()
        self.storage = InMemoryStorage(base_url="https://cdn.example.com/")
        patcher = patch(f"{MODULE}.default_storage", self.storage)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_unguessable_name(self):
        url = save_public("job-1.txt", b"log")
        self.assertTrue(url.startswith(f"https://cdn.example.com/{STORAGE_FOLDER}/job-1-"))
        self.assertTrue(url.endswith(".txt"))
        self.assertNotEqual(url, save_public("job-1.txt", b"log"))
        name = url.removeprefix("https://cdn.example.com/")
        with self.storage.open(name) as f:
            self.assertEqual(f.read(), b"log")

    def test_relative_url(self):
        """FileSystemStorage, without AWS, returns a relative url, which is made absolute."""
        self.storage = InMemoryStorage(base_url="/media/")
        with patch(f"{MODULE}.default_storage", self.storage):
            url = save_public("job.txt", b"log")
        self.assertTrue(url.startswith(f"{smarter_settings.environment_url.rstrip('/')}/media/{STORAGE_FOLDER}/"))


class TestEmailJobLogCommand(InfrastructureTestBase):
    """Test manage.py email_job_log."""

    def setUp(self):
        super().setUp()
        self.email = InMemoryEmailService()
        configure_email(lambda: self.email)
        # never save to the real S3 bucket.
        self.storage = InMemoryStorage(base_url="https://cdn.example.com/")
        patcher = patch(f"{MODULE}.default_storage", self.storage)
        patcher.start()
        self.addCleanup(patcher.stop)
        handle, name = tempfile.mkstemp(suffix=".log")
        os.close(handle)
        self.log = Path(name)
        self.addCleanup(self.log.unlink, missing_ok=True)

    def call(self, **options) -> str:
        stdout = StringIO()
        call_command("email_job_log", file=str(self.log), stdout=stdout, **options)
        return stdout.getvalue()

    def test_success(self):
        self.log.write_text("--- python manage.py migrate\nOK <done>\n", encoding="utf-8")
        output = self.call(job="smarter-job-init")
        self.assertIn("Emailed the log", output)
        self.assertEqual(len(self.email.outbox), 1)
        sent = self.email.outbox[0]
        self.assertEqual(sent.recipients, [str(smarter_settings.email_admin)])
        self.assertEqual(sent.bcc, [])
        self.assertIn("smarter-job-init SUCCEEDED", sent.subject)
        self.assertIn("(2 lines, 39 bytes) is attached as smarter-job-init-", sent.body)
        self.assertEqual(len(sent.attachments), 1)
        attachment = sent.attachments[0]
        self.assertRegex(attachment.filename, r"^smarter-job-init-\d{8}T\d{6}Z\.txt$")
        self.assertEqual(attachment.content_type, "text/plain")
        self.assertEqual(attachment.content, b"--- python manage.py migrate\nOK <done>\n")

    def test_to(self):
        self.log.write_text("OK\n", encoding="utf-8")
        self.call(to="ops@example.com")
        sent = self.email.outbox[0]
        self.assertEqual(sent.recipients, ["ops@example.com"])
        self.assertEqual(sent.bcc, [str(smarter_settings.email_admin)])

    def test_failure_status(self):
        self.log.write_text("FAILED: python manage.py migrate\n", encoding="utf-8")
        self.call(job="smarter-job-init", status=1)
        self.assertIn("FAILED (exit status 1)", self.email.outbox[0].subject)

    def test_redacted(self):
        self.log.write_text("Access denied for password s3cr3t-value\n", encoding="utf-8")
        with patch.dict(os.environ, {"SMARTER_MYSQL_ROOT_PASSWORD": "s3cr3t-value"}):
            self.call()
        content = self.email.outbox[0].attachments[0].content.decode("utf-8")
        self.assertNotIn("s3cr3t-value", content)
        self.assertIn(REDACTED, content)

    def test_whole_log_is_attached(self):
        self.log.write_text("\n".join(f"line {i}" for i in range(2000)), encoding="utf-8")
        self.call()
        content = self.email.outbox[0].attachments[0].content.decode("utf-8")
        self.assertTrue(content.startswith("line 0\n"))
        self.assertTrue(content.endswith("line 1999\n"))

    def test_too_large_is_saved_and_linked(self):
        self.log.write_text("\n".join(f"line {i}" for i in range(10)), encoding="utf-8")
        with patch.dict(os.environ, {"SMARTER_MYSQL_ROOT_PASSWORD": "line 5"}):
            self.call(job="smarter-job-init 1.0", max_attachment_bytes=10)
        sent = self.email.outbox[0]
        self.assertEqual(sent.attachments, [])
        self.assertIn("is too large to attach. It is public, at", sent.body)
        _, files = self.storage.listdir(STORAGE_FOLDER)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].startswith("smarter-job-init-10-"))
        self.assertIn(f'href="https://cdn.example.com/{STORAGE_FOLDER}/{files[0]}"', sent.body)
        with self.storage.open(f"{STORAGE_FOLDER}/{files[0]}") as f:
            content = f.read().decode("utf-8")
        self.assertIn("line 9", content)
        self.assertNotIn("line 5", content)
        self.assertIn(REDACTED, content)

    def test_too_large_and_not_saved(self):
        """If the log can be neither attached nor saved, the body carries its last lines."""
        self.log.write_text("\n".join(f"line {i}" for i in range(10)), encoding="utf-8")
        with patch(f"{MODULE}.save_public", side_effect=OSError("access denied")):
            self.call(max_attachment_bytes=10, lines=3)
        sent = self.email.outbox[0]
        self.assertEqual(sent.attachments, [])
        self.assertIn("could not be saved: access denied", sent.body)
        self.assertIn("Its last 3 lines:", sent.body)
        self.assertIn("line 9", sent.body)
        self.assertNotIn("line 6", sent.body)

    def test_missing_file(self):
        self.log.unlink()
        self.call()
        sent = self.email.outbox[0]
        self.assertIn("The log could not be read", sent.body)
        self.assertEqual(sent.attachments, [])

    def test_summary(self):
        """The summary file's text, redacted and escaped, is shown above the note about the log."""
        self.log.write_text("OK\n", encoding="utf-8")
        summary = self.log.with_suffix(".summary")
        self.addCleanup(summary.unlink, missing_ok=True)
        summary.write_text("Backup file: smarter.tar.gz <12 MiB>\nkey s3cr3t-value\n", encoding="utf-8")
        with patch.dict(os.environ, {"SMARTER_MYSQL_ROOT_PASSWORD": "s3cr3t-value"}):
            self.call(job="smarter-mysql-backup", summary=str(summary))
        body = self.email.outbox[0].body
        self.assertIn("<pre>Backup file: smarter.tar.gz &lt;12 MiB&gt;\nkey ********</pre>", body)
        self.assertNotIn("s3cr3t-value", body)
        self.assertLess(body.index("<pre>"), body.index("is attached as"))

    def test_missing_or_empty_summary(self):
        """A failed job may write no summary: the email is sent without one."""
        self.log.write_text("FAILED\n", encoding="utf-8")
        summary = self.log.with_suffix(".summary")
        self.addCleanup(summary.unlink, missing_ok=True)
        self.call(status=1, summary=str(summary))
        summary.write_text("\n", encoding="utf-8")
        self.call(status=1, summary=str(summary))
        self.assertEqual(len(self.email.outbox), 2)
        for sent in self.email.outbox:
            self.assertNotIn("<pre>", sent.body)
            self.assertEqual(len(sent.attachments), 1)

    def test_not_sent_does_not_fail(self):
        self.log.write_text("OK\n", encoding="utf-8")
        self.email.fail = "SMTP is down"
        output = self.call()
        self.assertIn("could not be emailed", output)
        self.assertEqual(self.email.outbox, [])
