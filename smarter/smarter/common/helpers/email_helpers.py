"""Helper class for sending email via AWS Simple Email Service using SMTP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Union

from django.conf import settings

from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterException
from smarter.lib.django.validators import SmarterValidator

from ..classes import Singleton


logger = logging.getLogger(__name__)


class EmailHelperException(SmarterException):
    """Base class for Email helper exceptions."""


class EmailHelper(metaclass=Singleton):
    """Helper class for sending emails."""

    @staticmethod
    def validate_mail_list(emails: Union[str, List[str]], quiet: bool = False) -> Union[List[str], None]:
        """Convert to a list and filter out any invalid email addresses."""
        if isinstance(emails, str):
            mailto_list = [emails]
        elif isinstance(emails, list):
            mailto_list = emails
        else:
            logger.warning("invalid email address list provided: %s", emails)
            return None

        valid_emails = [email for email in mailto_list if SmarterValidator.is_valid_email(email)]

        if len(valid_emails) != len(mailto_list) and set(mailto_list) != set(valid_emails) and not quiet:
            diff = set(mailto_list) != set(valid_emails)
            if diff != [""]:
                logger.warning(
                    "invalid email addresses were found in send list: %s", set(mailto_list) - set(valid_emails)
                )

        if len(valid_emails) == 0 and not quiet:
            logger.warning("no valid email addresses found in send list")
            return None

        return valid_emails

    # pylint: disable=too-many-arguments
    @staticmethod
    def send_email(subject, body, to: Union[str, List[str]], html=False, from_email=None, quiet: bool = False):
        """Send an email."""
        if not smarter_settings.smtp_is_configured:
            if not quiet:
                logger.warning(
                    "EmailHelper.send_email() quiet mode. SMTP not configured, would have sent subject '%s' to: %s",
                    subject,
                    to,
                )
            return

        mail_to = EmailHelper.validate_mail_list(emails=to, quiet=quiet)
        if mail_to in (None, []):
            return

        if quiet:
            logger.info("EmailHelper.send_email() quiet mode. would have sent subject '%s' to: %s", subject, mail_to)
            return

        if not mail_to:
            return

        if not smarter_settings.smtp_from_email:
            raise EmailHelperException("smtp_from_email not configured")
        if smarter_settings.smtp_host is None or smarter_settings.smtp_port is None:
            raise EmailHelperException("SMTP host or port not configured")
        if smarter_settings.smtp_username is None or smarter_settings.smtp_password is None:
            raise EmailHelperException("SMTP username or password not configured")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email or smarter_settings.smtp_from_email
        msg["To"] = ", ".join(mail_to)
        msg["Bcc"] = settings.SMARTER_EMAIL_ADMIN

        part2 = MIMEText(body, "html") if html else MIMEText(body)
        msg.attach(part2)

        try:
            with smtplib.SMTP(smarter_settings.smtp_host, smarter_settings.smtp_port) as server:
                if smarter_settings.smtp_use_tls:
                    server.starttls()
                server.login(smarter_settings.smtp_username, smarter_settings.smtp_password)
                server.sendmail(msg["From"], [msg["To"]], msg.as_string())
                logger.info("smtp email sent to %s: %s", to, subject)
        except (
            smtplib.SMTPDataError,
            smtplib.SMTPAuthenticationError,
            smtplib.SMTPConnectError,
            smtplib.SMTPHeloError,
            smtplib.SMTPRecipientsRefused,
            smtplib.SMTPSenderRefused,
            smtplib.SMTPServerDisconnected,
            smtplib.SMTPNotSupportedError,
        ) as e:
            logger.error(
                "smtp error while attempting to send email. error: %s from: %s to. %s", e, msg["From"], msg["To"]
            )
            if smarter_settings.developer_mode:
                raise EmailHelperException(f"Error sending email: {e}") from e
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "unexpected error while attempting to send email. error: %s from: %s to. %s", e, msg["From"], msg["To"]
            )
            if smarter_settings.developer_mode:
                raise EmailHelperException(f"Error sending email: {e}") from e


email_helper = EmailHelper()
