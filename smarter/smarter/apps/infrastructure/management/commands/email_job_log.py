"""
Email a job's log, by default to the platform's admin, ``smarter_settings.email_admin``.

The Helm chart's init Job tees its output to a file, and runs this command last, so that the
admin, or whoever ``--to`` names, learns how each install and upgrade went without reading
``kubectl logs``. Values of environment variables that look like credentials are redacted from
the log before it is sent. It is sent with
:data:`~smarter.apps.infrastructure.services.infrastructure` ``.email``, which also sends the
admin a blind copy when someone else is the recipient.

.. code-block:: console

    python manage.py email_job_log --file /tmp/job.log --job smarter-job-init --status 1
"""

import html
import os
import re
from pathlib import Path

from smarter.apps.infrastructure.services import infrastructure
from smarter.common.conf import smarter_settings
from smarter.lib.django.management.base import SmarterCommand

SECRET_ENV_NAME = re.compile(r"PASSWORD|SECRET|TOKEN|KEY", re.IGNORECASE)
"""Environment variables whose values are redacted from the log."""

MIN_SECRET_LENGTH = 6
"""Shorter values, e.g. a port number, are too common to redact."""

REDACTED = "********"


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


class Command(SmarterCommand):
    """Django manage.py email_job_log command."""

    help = (
        "Email the end of a job's log, by default to the platform's admin (smarter_settings.email_admin), with "
        "credentials redacted. Never fails, so that it never changes the job's outcome."
    )

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True, help="The log file.")
        parser.add_argument("--job", type=str, default="job", help="The job's name, for the subject.")
        parser.add_argument("--status", type=int, default=0, help="The job's exit status. 0 is success.")
        parser.add_argument(
            "--to", type=str, default="", help="The recipient. By default, smarter_settings.email_admin."
        )
        parser.add_argument("--lines", type=int, default=500, help="How many of the log's last lines to send.")

    def handle(self, *args, **options):
        self.handle_begin()
        job = options["job"]
        status = options["status"]
        lines = max(options["lines"], 1)
        outcome = "SUCCEEDED" if status == 0 else f"FAILED (exit status {status})"

        try:
            log = Path(options["file"]).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as e:
            log = [f"The log could not be read: {e}"]
        truncated = len(log) > lines
        text = redact("\n".join(log[-lines:]))

        subject = f"[{smarter_settings.environment_platform_domain}] {job} {outcome}"
        note = f"<p>The last {lines} lines of {len(log)}.</p>" if truncated else ""
        body = f"<p>{html.escape(job)} {html.escape(outcome)}.</p>{note}<pre>{html.escape(text)}</pre>"

        to = options["to"] or str(smarter_settings.email_admin)
        if infrastructure.email.send_email(subject=subject, body=body, to=to, html=True):
            self.stdout.write(self.style.SUCCESS(f"Emailed the log of {job} to {to}."))
            self.handle_completed_success()
        else:
            # the job's outcome is decided by the job, not by whether its log could be emailed.
            self.stdout.write(self.style.WARNING(f"The log of {job} could not be emailed to {to}."))
            self.handle_completed_failure(None, msg=f"The log of {job} could not be emailed to {to}.")
