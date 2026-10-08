"""
The email service: the platform's outgoing email.

Email does not depend on a cloud: Smarter sends it with SMTP, to any SMTP server, e.g. AWS
Simple Email Service's. So :class:`EmailService` is implemented by :class:`SMTPEmailService`,
for every cloud provider, and an email API, e.g. a cloud's, would be another implementation.

The platform uses it through :data:`smarter.apps.infrastructure.services.infrastructure`
``.email``. Tests replace it with :func:`configure_email`, e.g. with
:class:`InMemoryEmailService`.

.. code-block:: python

    from smarter.apps.infrastructure.services import infrastructure

    infrastructure.email.send_email(subject="Welcome!", body="<p>Hello</p>", to="user@example.com", html=True)
"""

import smtplib
from abc import abstractmethod
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Callable, List, Optional, Union

from smarter.common.conf import smarter_settings
from smarter.common.helpers.console_helpers import formatted_banner
from smarter.lib import logging
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.unittest import running_unit_tests

from ..const import InfrastructureServiceNames
from ..exceptions import EmailServiceError
from ..signals import email_failed, email_sent
from .base import InfrastructureService

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.INFRASTRUCTURE_LOGGING])

SMTP_ERRORS = (
    smtplib.SMTPDataError,
    smtplib.SMTPAuthenticationError,
    smtplib.SMTPConnectError,
    smtplib.SMTPHeloError,
    smtplib.SMTPRecipientsRefused,
    smtplib.SMTPSenderRefused,
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPNotSupportedError,
)


class EmailService(InfrastructureService):
    """The platform's outgoing email."""

    service_name = InfrastructureServiceNames.EMAIL
    error_class = EmailServiceError

    @abstractmethod
    def _deliver(self, message: MIMEMultipart, recipients: list[str], bcc: list[str]) -> None:
        """
        Deliver a message to its recipients, and blind copies to ``bcc``.

        The blind copies' addresses are not in the message's headers: they are only added to
        the envelope, so that no recipient sees them.

        :raises Exception: If it cannot be delivered.
        """

    @staticmethod
    def validate_mail_list(emails: Union[str, List[str]], quiet: bool = False) -> Optional[List[str]]:
        """
        Return the valid email addresses of a list.

        :param emails: An email address, or a list of them.
        :param quiet: True to not log invalid addresses.
        :returns: The valid addresses, or None if there are none.
        """
        if isinstance(emails, str):
            mailto_list = [emails]
        elif isinstance(emails, list):
            mailto_list = emails
        else:
            logger.warning("%s invalid email address list provided: %s", __name__, emails)
            return None

        valid_emails = [email for email in mailto_list if SmarterValidator.is_valid_email(email)]
        invalid_emails = set(mailto_list) - set(valid_emails)
        if invalid_emails and not quiet:
            logger.warning("%s invalid email addresses were found in send list: %s", __name__, invalid_emails)
        if not valid_emails:
            if not quiet:
                logger.warning("%s no valid email addresses found in send list", __name__)
            return None
        return valid_emails

    def message(self, subject: str, body: str, to: list[str], html: bool = False, from_email=None) -> MIMEMultipart:
        """
        Return a message, from ``smarter_settings.smtp_from_email`` unless ``from_email`` is given.

        It has no ``Bcc`` header: blind copies are added to the envelope by :meth:`_deliver`.
        """
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = from_email or smarter_settings.smtp_from_email
        message["To"] = ", ".join(to)
        message.attach(MIMEText(body, "html") if html else MIMEText(body))
        return message

    def log_not_sent(self, subject: str, to: Union[str, List[str]]) -> None:
        """
        Log an email that was not sent because the service is not ready.

        :param subject: The email's subject.
        :param to: The email's recipients.
        """
        logger.warning(
            "%s %s is not configured. Would have sent '%s' to: %s", self.formatted_class_name, self, subject, to
        )

    @staticmethod
    def admin_bcc(recipients: list[str]) -> list[str]:
        """
        The blind copy to the platform's admin, ``smarter_settings.email_admin``.

        :param recipients: The email's recipients, who need no copy.
        :returns: The admin's address, or nothing if there is no valid admin address, or the admin is a recipient.
        """
        admin = smarter_settings.email_admin
        if not admin or not SmarterValidator.is_valid_email(str(admin)):
            return []
        if str(admin).lower() in {recipient.lower() for recipient in recipients}:
            return []
        return [str(admin)]

    # pylint: disable=too-many-arguments
    def send_email(
        self,
        subject: str,
        body: str,
        to: Union[str, List[str]],
        html: bool = False,
        from_email: Optional[str] = None,
        quiet: bool = False,
        bcc_admin: bool = True,
    ) -> bool:
        """
        Send an email.

        Failures are logged, and announced with
        :data:`~smarter.apps.infrastructure.signals.email_failed`, rather than raised, so that
        email never breaks the request that sends it.

        :param subject: The subject.
        :param body: The body, HTML if ``html`` is True.
        :param to: The recipient, or recipients. Invalid addresses are dropped.
        :param html: True if the body is HTML.
        :param from_email: The sender, by default ``smarter_settings.smtp_from_email``.
        :param quiet: True to only log what would have been sent.
        :param bcc_admin: Send a blind copy to the platform's admin, ``smarter_settings.email_admin``.
            Pass False for an email that carries a secret, e.g. a password reset link, which only
            its recipient may see.
        :returns: True if the email was sent.
        """
        if not self.ready:
            if not quiet:
                self.log_not_sent(subject, to)
            return False

        recipients = self.validate_mail_list(emails=to, quiet=quiet)
        if not recipients:
            return False
        if quiet:
            logger.debug("%s quiet mode. Would have sent '%s' to: %s", self.formatted_class_name, subject, recipients)
            return False

        message = self.message(subject, body, recipients, html=html, from_email=from_email)
        bcc = self.admin_bcc(recipients) if bcc_admin else []
        try:
            self._deliver(message, recipients, bcc)
        except SystemExit:
            raise
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s could not send '%s' from %s to %s: %s",
                self.formatted_class_name,
                subject,
                message["From"],
                recipients,
                e,
            )
            self.send(email_failed, subject=subject, recipients=recipients, error=str(e))
            return False
        logger.info("%s sent '%s' to %s", self.formatted_class_name, subject, recipients)
        self.send(email_sent, subject=subject, recipients=recipients)
        return True


class SMTPEmailService(EmailService):
    """
    Email, with SMTP, configured by the ``smtp_*`` settings of ``smarter_settings``.

    In the unit tests, nothing is sent, unless ``allow_in_tests`` is True, so that tests never
    email real people.

    :param allow_in_tests: Send email in the unit tests.
    :param smtp_class: The SMTP client class, e.g. a fake.
    """

    def __init__(self, allow_in_tests: bool = False, smtp_class: Callable[..., smtplib.SMTP] = smtplib.SMTP, **kwargs):
        super().__init__(provider_name="smtp", **kwargs)
        self.allow_in_tests = allow_in_tests
        self.smtp_class = smtp_class

    @property
    def ready(self) -> bool:
        if running_unit_tests() and not self.allow_in_tests:
            return False
        return bool(smarter_settings.smtp_is_configured)

    def log_not_sent(self, subject: str, to: Union[str, List[str]]) -> None:
        """
        Log an email that was not sent, with instructions for configuring SMTP.

        SMTP is optional, so this is logged for each email that is not sent, rather than raised.
        In the unit tests, where email is never sent, a one-line warning is logged instead.
        """
        if running_unit_tests() and not self.allow_in_tests:
            super().log_not_sent(subject, to)
            return
        logger.error(
            formatted_banner(
                f"[EMAIL NOT SENT] SMTP is not configured, so '{subject}' was not sent to: {to}",
                "To send email, add your SMTP server's credentials to .env, and restart the platform:",
                "",
                "    SMARTER_SMTP_USERNAME=<your SMTP username>",
                "    SMARTER_SMTP_PASSWORD=<your SMTP password>",
                "    SMARTER_SMTP_HOST=<your SMTP server>  # not needed for AWS SES when AWS_REGION is set",
                "    SMARTER_SMTP_PORT=587                 # optional",
                "",
                "With AWS Simple Email Service, create SMTP credentials in the SES console:",
                "https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html",
            )
        )

    def _deliver(self, message: MIMEMultipart, recipients: list[str], bcc: list[str]) -> None:
        if not smarter_settings.smtp_from_email:
            raise EmailServiceError("smtp_from_email is not configured")
        if smarter_settings.smtp_host is None or smarter_settings.smtp_port is None:
            raise EmailServiceError("SMTP host or port is not configured")
        if smarter_settings.smtp_username is None or smarter_settings.smtp_password is None:
            raise EmailServiceError("SMTP username or password is not configured")
        with self.smtp_class(smarter_settings.smtp_host, smarter_settings.smtp_port) as server:
            if smarter_settings.smtp_use_tls:
                server.starttls()
            server.login(
                smarter_settings.smtp_username.get_secret_value(), smarter_settings.smtp_password.get_secret_value()
            )
            # the envelope's recipients include the blind copies, which the message's headers do not.
            server.sendmail(message["From"], recipients + bcc, message.as_string())


@dataclass
class SentEmail:
    """An email that :class:`InMemoryEmailService` sent."""

    subject: str
    sender: str
    recipients: list[str]
    bcc: list[str] = field(default_factory=list)
    body: str = ""
    headers: dict[str, str] = field(default_factory=dict)


class InMemoryEmailService(EmailService):
    """
    Email that is kept in :attr:`outbox`, for tests and local development.

    :param ready: Whether the service is ready.
    """

    def __init__(self, ready: bool = True, **kwargs):
        super().__init__(provider_name="memory", **kwargs)
        self._ready = ready
        self.outbox: list[SentEmail] = []
        self.fail: Optional[str] = None
        """Set to make delivery fail with this error."""

    @property
    def ready(self) -> bool:
        return self._ready

    def _deliver(self, message: MIMEMultipart, recipients: list[str], bcc: list[str]) -> None:
        if self.fail:
            raise EmailServiceError(self.fail)
        payload = message.get_payload()
        body = payload[0].get_payload() if isinstance(payload, list) and payload else str(payload)
        self.outbox.append(
            SentEmail(
                subject=str(message["Subject"]),
                sender=str(message["From"]),
                recipients=list(recipients),
                bcc=list(bcc),
                body=str(body),
                headers={key: str(value) for key, value in message.items()},
            )
        )


_email_factory: Optional[Callable[[], EmailService]] = None
_email: Optional[EmailService] = None


def configure_email(factory: Optional[Callable[[], EmailService]]) -> None:
    """
    Set the factory of the email service that :func:`get_email` returns.

    :param factory: Returns the service, or None to restore the default, :class:`SMTPEmailService`.
    """
    global _email_factory, _email  # pylint: disable=global-statement
    _email_factory = factory
    _email = None


def get_email() -> EmailService:
    """Return the email service, which is created once."""
    global _email  # pylint: disable=global-statement
    if _email is None:
        _email = _email_factory() if _email_factory is not None else SMTPEmailService()
    return _email


__all__ = [
    "EmailService",
    "InMemoryEmailService",
    "SMTPEmailService",
    "SentEmail",
    "configure_email",
    "get_email",
]
