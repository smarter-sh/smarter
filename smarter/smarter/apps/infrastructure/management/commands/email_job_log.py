"""
Email a job's log, by default to the platform's admin, ``smarter_settings.email_admin``, and post it to Slack.

The Helm chart's init Job tees its output to a file, and runs this command last, so that the
admin, or whoever ``--to`` names, learns how each install and upgrade went without reading
``kubectl logs``. Values of environment variables that look like credentials are redacted from
the log before it is sent.

``--summary`` names a second, short file, whose text is shown at the top of the email's body, for
example the name, size and location of the file that a backup Job saved. The Helm chart's scheduled
database backup Job uses it.

The whole log is attached to the email. A log larger than ``--max-attachment-bytes`` would
exceed the SMTP server's message size limit, so it is saved instead to the platform's default
file storage, which is public (an S3 bucket with a ``public-read`` ACL, served by the CDN), under
an unguessable name, and the email links to it. If it cannot be saved, the email carries the
log's last ``--lines`` lines instead.

It is sent with :data:`~smarter.apps.infrastructure.services.infrastructure` ``.email``, which
also sends the admin a blind copy when someone else is the recipient.

``--slack-channel`` also posts the job's outcome to a Slack channel, whatever became of the email,
with :data:`~smarter.apps.infrastructure.services.infrastructure` ``.slack``, when Slack is
configured (``SMARTER_SLACK_BOT_TOKEN``). The message says whether the job succeeded, followed by
the summary, if any, and the whole log, redacted, is uploaded into the message's thread, as the same
file that the email attaches. If it cannot be uploaded, e.g. because the bot lacks the scope
``files:write``, the thread gets the log's last lines that fit in a Slack message instead, and the
link to the log, if it was saved to public storage. Text from the log, the summary and the job's
name is escaped, so that it cannot mention anyone, e.g. with ``<!channel>``.

The command never fails, so that it never changes the job's outcome: neither email nor Slack
changes its exit status.

.. code-block:: console

    python manage.py email_job_log --file /tmp/job.log --job smarter-job-init --status 1
    python manage.py email_job_log --file /tmp/backup.log --summary /tmp/backup-summary.txt --job smarter-mysql-backup
    python manage.py email_job_log --file /tmp/job.log --job smarter-job-init --slack-channel smarter
"""

import html
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.text import slugify

from smarter.apps.infrastructure.services import EmailAttachment, infrastructure
from smarter.apps.infrastructure.services.slack import escape
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.django.validators import SmarterValidator

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

SECRET_ENV_NAME = re.compile(r"PASSWORD|SECRET|TOKEN|KEY", re.IGNORECASE)
"""Environment variables whose values are redacted from the log."""

MIN_SECRET_LENGTH = 6
"""Shorter values, e.g. a port number, are too common to redact."""

REDACTED = "********"

MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024
"""The largest log that is attached.

Base64 encoding adds a third, and AWS SES accepts 10 MB messages.
"""

STORAGE_FOLDER = "job-logs"
"""The folder of the default file storage that holds logs too large to attach."""

SLACK_TAIL_CHARACTERS = 3500
"""The most characters of the log's last lines that are posted to Slack when the log cannot be uploaded.

Slack shortens a message's text after 4,000 characters.
"""


def secret_values() -> list[str]:
    """
    The values of the environment variables that look like credentials, longest first.

    :returns: The values to redact.
    """
    values = {
        value for name, value in os.environ.items() if SECRET_ENV_NAME.search(name) and len(value) >= MIN_SECRET_LENGTH
    }
    return sorted(values, key=len, reverse=True)


def redact(text: str) -> str:
    """
    Replace the values of the environment variables that look like credentials.

    :param text: The log.
    :returns: The log, redacted.
    """
    for value in secret_values():
        text = text.replace(value, REDACTED)
    return text


def read_summary_text(filename: str) -> str:
    """
    The summary of a job: the text of ``--summary``, redacted.

    A summary that is missing or empty, for example because the job failed before it wrote one, is
    left out, and the email and Slack message are sent without it.

    :param filename: The summary file, or an empty string for none.
    :returns: The summary, or an empty string.
    """
    if not filename:
        return ""
    try:
        return redact(Path(filename).read_text(encoding="utf-8", errors="replace")).strip()
    except OSError as e:
        logger.warning("%s.read_summary_text() could not read the summary %s: %s", logger_prefix, filename, e)
        return ""


def slack_code_block(text: str) -> str:
    """
    Return text as a Slack ``mrkdwn`` code block, escaped.

    :param text: The text, e.g. a log's last lines.
    :returns: The code block. Backticks that would end it early are broken up.
    """
    return "```\n" + escape(text).replace("```", "`\u200b``") + "\n```"


def slack_tail(log: list[str], limit: int = SLACK_TAIL_CHARACTERS) -> list[str]:
    """
    The log's last lines that fit in a Slack message, once escaped.

    :param log: The log's lines.
    :param limit: The most characters, escaped, newlines included.
    :returns: The last lines, in order. If even the last line is too long, its end.
    """
    tail: list[str] = []
    size = 0
    for line in reversed(log):
        size += len(escape(line)) + 1
        if size > limit:
            break
        tail.append(line)
    if not tail and log:
        # an escaped character is at most five characters, e.g. &amp;
        end = log[-1][-limit:]
        tail = [end if len(escape(end)) <= limit else log[-1][-(limit // 5) :]]
    return list(reversed(tail))


def save_public(filename: str, content: bytes) -> str:
    """
    Save a file to the platform's default file storage, and return its public URL.

    The default file storage is an S3 bucket whose objects are ``public-read`` and served by the
    CDN, or, without AWS, the local file system. The file's name ends with a random token, so that
    its URL cannot be guessed.

    :param filename: The file's name, e.g. ``smarter-job-init-20261015T120000Z.txt``.
    :param content: The file's contents.
    :returns: The file's absolute URL.
    :raises Exception: If the file cannot be saved.
    """
    stem, dot, suffix = filename.rpartition(".")
    name = f"{STORAGE_FOLDER}/{stem}-{secrets.token_urlsafe(16)}{dot}{suffix}"
    name = default_storage.save(name, ContentFile(content))
    url = default_storage.url(name)
    # FileSystemStorage's url is relative.
    return url if SmarterValidator.is_valid_url(url) else urljoin(smarter_settings.environment_url, url)


class Command(SmarterCommand):
    """Django manage.py email_job_log command."""

    help = (
        "Email a job's log, by default to the platform's admin (smarter_settings.email_admin), with credentials "
        "redacted. The log is attached, or, if it is too large, saved to the platform's public file storage and "
        "linked. With --slack-channel, also post the outcome to Slack, with the log in the message's thread. "
        "Never fails, so that it never changes the job's outcome."
    )

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True, help="The log file.")
        parser.add_argument("--job", type=str, default="job", help="The job's name, for the subject.")
        parser.add_argument("--status", type=int, default=0, help="The job's exit status. 0 is success.")
        parser.add_argument(
            "--to", type=str, default="", help="The recipient. By default, smarter_settings.email_admin."
        )
        parser.add_argument(
            "--summary",
            type=str,
            default="",
            help="A short file whose text is shown at the top of the email, e.g. what a backup saved and where.",
        )
        parser.add_argument(
            "--max-attachment-bytes",
            type=int,
            default=MAX_ATTACHMENT_BYTES,
            help="The largest log that is attached. A larger one is saved to public file storage and linked.",
        )
        parser.add_argument(
            "--slack-channel",
            type=str,
            default="",
            help=(
                "Also post the job's outcome to this Slack channel, e.g. smarter, with the log in the message's thread. "
                "Needs SMARTER_SLACK_BOT_TOKEN, a bot with the scopes chat:write and files:write, in the channel. "
                "Empty: don't post."
            ),
        )
        parser.add_argument(
            "--lines",
            type=int,
            default=500,
            help="How many of the log's last lines to send in the body if the log can be neither attached nor saved.",
        )

    # pylint: disable=too-many-locals
    def handle(self, *args, **options):
        self.handle_begin()
        job = options["job"]
        status = options["status"]
        lines = max(options["lines"], 1)
        outcome = "SUCCEEDED" if status == 0 else f"FAILED (exit status {status})"

        log: Optional[list[str]] = None
        read_error = ""
        try:
            log = redact(Path(options["file"]).read_text(encoding="utf-8", errors="replace")).splitlines()
        except OSError as e:
            read_error = str(e)
            note = f"<p>The log could not be read: {html.escape(read_error)}</p>"

        attachments: list[EmailAttachment] = []
        filename = ""
        content = b""
        url = ""
        if log is not None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            filename = f"{slugify(job) or 'job'}-{timestamp}.txt"
            content = ("\n".join(log) + "\n").encode("utf-8")
            size = f"{len(log)} lines, {len(content):,} bytes"
            if len(content) <= options["max_attachment_bytes"]:
                attachments.append(EmailAttachment(filename=filename, content=content))
                note = f"<p>The log ({size}) is attached as {html.escape(filename)}.</p>"
            else:
                try:
                    url = save_public(filename, content)
                    note = (
                        f"<p>The log ({size}) is too large to attach. It is public, at "
                        f'<a href="{html.escape(url)}">{html.escape(url)}</a></p>'
                    )
                # pylint: disable=broad-except
                except Exception as e:
                    logger.error("%s.handle() could not save the log of %s: %s", logger_prefix, job, e)
                    tail = "\n".join(log[-lines:])
                    note = (
                        f"<p>The log ({size}) is too large to attach, and could not be saved: "
                        f"{html.escape(str(e))}</p><p>Its last {min(lines, len(log))} lines:</p>"
                        f"<pre>{html.escape(tail)}</pre>"
                    )

        subject = f"[{smarter_settings.environment_platform_domain}] {job} {outcome}"
        summary = read_summary_text(options["summary"])
        summary_html = f"<pre>{html.escape(summary)}</pre>" if summary else ""
        body = f"<p>{html.escape(job)} {html.escape(outcome)}.</p>{summary_html}{note}"

        to = options["to"] or str(smarter_settings.email_admin)
        emailed = infrastructure.email.send_email(subject=subject, body=body, to=to, html=True, attachments=attachments)
        if emailed:
            self.stdout.write(self.style.SUCCESS(f"Emailed the log of {job} to {to}."))
        else:
            self.stdout.write(self.style.WARNING(f"The log of {job} could not be emailed to {to}."))

        channel = options["slack_channel"].strip().lstrip("#")
        if channel:
            try:
                self.post_to_slack(channel, subject, status, summary, log, filename, content, url, read_error)
            # pylint: disable=broad-except
            except Exception as e:
                logger.error("%s.handle() could not post the log of %s to Slack: %s", logger_prefix, job, e)
                self.stdout.write(self.style.WARNING(f"The log of {job} could not be posted to Slack #{channel}."))

        # the job's outcome is decided by the job, not by whether its log could be emailed or posted.
        if emailed:
            self.handle_completed_success()
        else:
            self.handle_completed_failure(None, msg=f"The log of {job} could not be emailed to {to}.")

    # pylint: disable=too-many-arguments
    def post_to_slack(
        self,
        channel: str,
        title: str,
        status: int,
        summary: str,
        log: Optional[list[str]],
        filename: str,
        content: bytes,
        url: str,
        read_error: str,
    ) -> bool:
        """
        Post the job's outcome to a Slack channel, with its log in the message's thread.

        The message is the outcome, with an emoji, and the summary, if any. The whole log is
        uploaded into its thread. If it cannot be uploaded, the thread gets the log's last lines
        that fit in a message, and the link to the log, if it was saved to public storage.

        :param channel: The channel's name, e.g. ``smarter``, or its id.
        :param title: The email's subject, e.g. ``[platform.example.com] smarter-job-init SUCCEEDED``.
        :param status: The job's exit status.
        :param summary: The job's summary, redacted, or an empty string.
        :param log: The log's lines, redacted, or None if it could not be read.
        :param filename: The log's file name, as the email attaches it.
        :param content: The log, as the email attaches it.
        :param url: The log's public url, if it was saved to public storage, or an empty string.
        :param read_error: Why the log could not be read, or an empty string.
        :returns: True if the outcome was posted, whether or not the log was.
        """
        slack = infrastructure.slack
        if not slack.ready:
            logger.warning(
                "%s.post_to_slack() Slack is not configured. Nothing was posted to %s.", logger_prefix, channel
            )
            self.stdout.write(
                self.style.WARNING(
                    f"Slack is not configured (SMARTER_SLACK_BOT_TOKEN). Nothing was posted to #{channel}."
                )
            )
            return False

        emoji = ":white_check_mark:" if status == 0 else ":x:"
        text = f"{emoji} *{escape(title)}*"
        if summary:
            text += "\n" + slack_code_block(summary)
        if read_error:
            text += f"\nThe log could not be read: {escape(read_error)}"
        message = slack.post_message(channel, text)
        if message is None:
            self.stdout.write(self.style.WARNING(f"The outcome could not be posted to Slack #{channel}."))
            return False

        if log is None:
            self.stdout.write(self.style.SUCCESS(f"Posted the outcome to Slack #{channel}."))
            return True
        if slack.upload_file(message.channel_id, filename, content, thread_ts=message.ts):
            self.stdout.write(self.style.SUCCESS(f"Posted the outcome and the log to Slack #{channel}."))
            return True

        tail = slack_tail(log)
        reply = f"The log ({len(log)} lines, {len(content):,} bytes) could not be uploaded. Its last {len(tail)} lines:"
        reply += "\n" + slack_code_block("\n".join(tail))
        if url:
            reply += f"\nThe whole log: {escape(url)}"
        if slack.post_message(message.channel_id, reply, thread_ts=message.ts):
            self.stdout.write(self.style.WARNING(f"Posted the outcome and the log's last lines to Slack #{channel}."))
        else:
            self.stdout.write(self.style.WARNING(f"Posted the outcome to Slack #{channel}, without the log."))
        return True
