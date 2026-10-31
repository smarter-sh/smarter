"""
Test manage.py email_job_log.

No email is sent, and nothing is posted to Slack: the tests use the in-memory email and Slack
services. Nothing is saved to S3: the default file storage is replaced with an in-memory one.
"""

import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.files.storage import InMemoryStorage
from django.core.management import call_command

from smarter.apps.infrastructure.management.commands.email_job_log import (
    REDACTED,
    SLACK_TAIL_CHARACTERS,
    STORAGE_FOLDER,
    redact,
    save_public,
    secret_values,
    slack_code_block,
    slack_tail,
)
from smarter.apps.infrastructure.services import (
    InMemoryEmailService,
    InMemorySlackService,
    configure_email,
    configure_slack,
)
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


class TestSlackHelpers(InfrastructureTestBase):
    """Test slack_tail() and slack_code_block()."""

    def test_tail_fits(self):
        log = [f"line {i}" for i in range(1000)]
        tail = slack_tail(log)
        self.assertEqual(tail[-1], "line 999")
        self.assertLessEqual(len("\n".join(tail)), SLACK_TAIL_CHARACTERS)
        self.assertGreater(len("\n".join(log[-len(tail) - 1 :])) + 1, SLACK_TAIL_CHARACTERS)
        self.assertEqual(slack_tail(["a", "b"]), ["a", "b"])
        self.assertEqual(slack_tail([]), [])

    def test_tail_counts_escaped_characters(self):
        self.assertEqual(slack_tail(["<<", ">>", "&"], limit=15), [">>", "&"])

    def test_long_last_line(self):
        self.assertEqual(slack_tail(["first", "x" * 50 + "end"], limit=10), ["xxxxxxxend"])
        self.assertEqual(slack_tail(["<" * 50], limit=10), ["<<"])

    def test_code_block(self):
        self.assertEqual(slack_code_block("a <b> ```c```"), "```\na &lt;b&gt; `\u200b``c`\u200b``\n```")


class TestEmailJobLogSlack(InfrastructureTestBase):
    """Test manage.py email_job_log --slack-channel."""

    def setUp(self):
        super().setUp()
        self.email = InMemoryEmailService()
        configure_email(lambda: self.email)
        self.slack = InMemorySlackService()
        configure_slack(lambda: self.slack)
        self.storage = InMemoryStorage(base_url="https://cdn.example.com/")
        patcher = patch(f"{MODULE}.default_storage", self.storage)
        patcher.start()
        self.addCleanup(patcher.stop)
        handle, name = tempfile.mkstemp(suffix=".log")
        os.close(handle)
        self.log = Path(name)
        self.addCleanup(self.log.unlink, missing_ok=True)
        self.log.write_text("--- python manage.py migrate\nOK <done>\n", encoding="utf-8")

    def call(self, **options) -> str:
        stdout = StringIO()
        call_command("email_job_log", file=str(self.log), stdout=stdout, **options)
        return stdout.getvalue()

    def test_no_channel_posts_nothing(self):
        self.call()
        self.assertEqual((self.slack.messages, self.slack.files), ([], []))

    def test_success(self):
        """The outcome is posted, and the log, as the email attaches it, is uploaded into its thread."""
        output = self.call(job="smarter-job-init", slack_channel="#smarter")
        self.assertIn("Posted the outcome and the log to Slack #smarter.", output)
        self.assertEqual(len(self.slack.messages), 1)
        message = self.slack.messages[0]
        self.assertEqual(message.channel, "smarter")
        self.assertEqual(
            message.text,
            f":white_check_mark: *[{smarter_settings.environment_platform_domain}] smarter-job-init SUCCEEDED*",
        )
        self.assertEqual(len(self.slack.files), 1)
        uploaded = self.slack.files[0]
        attachment = self.email.outbox[0].attachments[0]
        self.assertEqual((uploaded.filename, uploaded.content), (attachment.filename, attachment.content))
        self.assertEqual((uploaded.channel_id, uploaded.thread_ts), (message.channel_id, message.ts))

    def test_failure_with_summary(self):
        """A failed job is posted with :x:, and the summary, redacted and escaped, in a code block."""
        summary = self.log.with_suffix(".summary")
        self.addCleanup(summary.unlink, missing_ok=True)
        summary.write_text("Backup file: smarter.tar.gz <12 MiB>\nkey s3cr3t-value\n", encoding="utf-8")
        self.log.write_text("FAILED: <!channel> s3cr3t-value\n", encoding="utf-8")
        with patch.dict(os.environ, {"SMARTER_MYSQL_ROOT_PASSWORD": "s3cr3t-value"}):
            self.call(job="smarter-mysql-backup <1.0>", status=2, summary=str(summary), slack_channel="smarter")
        text = self.slack.messages[0].text
        self.assertTrue(text.startswith(":x: *["))
        self.assertIn("smarter-mysql-backup &lt;1.0&gt; FAILED (exit status 2)*", text)
        self.assertIn("```\nBackup file: smarter.tar.gz &lt;12 MiB&gt;\nkey ********\n```", text)
        self.assertNotIn("s3cr3t-value", text)
        content = self.slack.files[0].content.decode("utf-8")
        self.assertEqual(content, f"FAILED: <!channel> {REDACTED}\n")

    def test_upload_fails(self):
        """Without files:write, the thread gets the log's last lines instead."""
        self.slack.errors["files.getUploadURLExternal"] = "missing_scope"
        self.log.write_text("\n".join(f"line <{i}>" for i in range(2000)), encoding="utf-8")
        output = self.call(slack_channel="smarter")
        self.assertIn("Posted the outcome and the log's last lines to Slack #smarter.", output)
        self.assertEqual(self.slack.files, [])
        message, reply = self.slack.messages
        self.assertEqual((reply.channel, reply.thread_ts), (message.channel_id, message.ts))
        self.assertIn("could not be uploaded. Its last", reply.text)
        self.assertIn("line &lt;1999&gt;\n```", reply.text)
        self.assertNotIn("line <", reply.text)
        self.assertNotIn("The whole log:", reply.text)
        self.assertLess(len(reply.text), 4000)

    def test_upload_fails_with_public_log(self):
        """A log that was saved to public storage is linked from the reply."""
        self.slack.errors["files.completeUploadExternal"] = "not_in_channel"
        self.call(max_attachment_bytes=10, slack_channel="smarter")
        reply = self.slack.messages[1].text
        _, files = self.storage.listdir(STORAGE_FOLDER)
        self.assertIn(f"The whole log: https://cdn.example.com/{STORAGE_FOLDER}/{files[0]}", reply)

    def test_reply_fails(self):
        self.slack.errors["files.getUploadURLExternal"] = "missing_scope"
        with patch.object(self.slack, "post_message", side_effect=[MagicMock(channel_id="C1", ts="1.1"), None]):
            output = self.call(slack_channel="smarter")
        self.assertIn("Posted the outcome to Slack #smarter, without the log.", output)

    def test_message_fails(self):
        self.slack.errors["chat.postMessage"] = "channel_not_found"
        output = self.call(slack_channel="nope")
        self.assertIn("The outcome could not be posted to Slack #nope.", output)
        self.assertIn("Emailed the log", output)
        self.assertEqual(self.slack.files, [])

    def test_missing_log(self):
        """A log that can't be read is reported in the message, and nothing is uploaded."""
        self.log.unlink()
        output = self.call(slack_channel="smarter")
        self.assertIn("Posted the outcome to Slack #smarter.", output)
        self.assertIn("The log could not be read:", self.slack.messages[0].text)
        self.assertEqual(self.slack.files, [])

    def test_slack_not_ready(self):
        configure_slack(lambda: InMemorySlackService(ready=False))
        output = self.call(slack_channel="smarter")
        self.assertIn("Slack is not configured (SMARTER_SLACK_BOT_TOKEN). Nothing was posted to #smarter.", output)
        self.assertEqual(len(self.email.outbox), 1)

    def test_slack_errors_do_not_change_the_outcome(self):
        """The command never fails, whatever Slack or email do."""
        self.email.fail = "SMTP is down"
        with (
            patch.object(self.slack, "post_message", side_effect=RuntimeError("bug")),
            patch(f"{MODULE}.logger") as logger,
        ):
            output = self.call(slack_channel="smarter")
        self.assertIn("could not be emailed", output)
        self.assertIn("could not be posted to Slack #smarter.", output)
        self.assertIn("bug", str(logger.error.call_args))
