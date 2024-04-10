# -*- coding: utf-8 -*-
"""Helper class for sending email via AWS Simple Email Service using SMTP."""
import logging
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Union

from django.conf import settings

from smarter.common.const import VALID_EMAIL_PATTERN


logger = logging.getLogger(__name__)


class EmailHelper:
    """Helper class for sending emails."""

    def validate_mail_list(emails: Union[str, List[str]], quiet: bool = False) -> List[str]:
        """Convert to a list and filter out any invalid email addresses."""
        if isinstance(emails, str):
            mailto_list = [emails]

        valid_emails = [email for email in mailto_list if re.match(VALID_EMAIL_PATTERN, email)]

        if len(valid_emails) != len(mailto_list) and not quiet:
            logger.warning("invalid email addresses were found in send list: %s", set(mailto_list) - set(valid_emails))

        if len(valid_emails) == 0 and not quiet:
            logger.warning("no valid email addresses found in send list")
            return None

        return valid_emails

    # pylint: disable=too-many-arguments
    @staticmethod
    def send_email(subject, body, to: Union[str, List[str]], html=False, from_email=None, quiet: bool = False):
        """Send an email."""
        mail_to = EmailHelper.validate_mail_list(emails=to, quiet=quiet)

        if quiet:
            logger.info("EmailHelper.send_email() quite mode. would have sent subject '%s' to: %s", subject, mail_to)
            return

        if not mail_to:
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email or settings.SMTP_FROM_EMAIL
        msg["To"] = ", ".join(mail_to)

        part2 = MIMEText(body, "html") if html else MIMEText(body)
        msg.attach(part2)

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(msg["From"], [msg["To"]], msg.as_string())
            logger.info("smtp email sent to %s: %s", to, subject)
