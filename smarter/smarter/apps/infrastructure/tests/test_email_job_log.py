"""
Test manage.py email_job_log.

No email is sent: the tests use the in-memory email service.
"""

import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command

from smarter.apps.infrastructure.management.commands.email_job_log import (
    REDACTED,
    redact,
    secret_values,
)
from smarter.apps.infrastructure.services import InMemoryEmailService, configure_email
from smarter.common.conf import smarter_settings

from .base import InfrastructureTestBase


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


class TestEmailJobLogCommand(InfrastructureTestBase):
    """Test manage.py email_job_log."""

    def setUp(self):
        super().setUp()
        self.email = InMemoryEmailService()
        configure_email(lambda: self.email)
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
        self.assertIn("OK &lt;done&gt;", sent.body)

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
        self.assertNotIn("s3cr3t-value", self.email.outbox[0].body)
        self.assertIn(REDACTED, self.email.outbox[0].body)

    def test_truncated(self):
        self.log.write_text("\n".join(f"line {i}" for i in range(10)), encoding="utf-8")
        self.call(lines=3)
        body = self.email.outbox[0].body
        self.assertIn("The last 3 lines of 10.", body)
        self.assertIn("line 9", body)
        self.assertNotIn("line 6", body)

    def test_missing_file(self):
        self.log.unlink()
        self.call()
        self.assertIn("The log could not be read", self.email.outbox[0].body)

    def test_not_sent_does_not_fail(self):
        self.log.write_text("OK\n", encoding="utf-8")
        self.email.fail = "SMTP is down"
        output = self.call()
        self.assertIn("could not be emailed", output)
        self.assertEqual(self.email.outbox, [])
