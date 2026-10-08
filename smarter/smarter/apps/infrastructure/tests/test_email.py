"""
Test :mod:`smarter.apps.infrastructure.services.email`.

No email is sent: SMTP is a fake SMTP class, and the other tests use the in-memory email service.
"""

import smtplib
from unittest.mock import MagicMock, patch

from pydantic import SecretStr

from smarter.apps.infrastructure.services import (
    InMemoryEmailService,
    SMTPEmailService,
    configure_email,
    get_email,
    infrastructure,
)
from smarter.apps.infrastructure.services.email import EmailService
from smarter.apps.infrastructure.signals import email_failed, email_sent

from .base import InfrastructureTestBase

MODULE = "smarter.apps.infrastructure.services.email"


def smtp_settings(**overrides) -> MagicMock:
    settings = MagicMock(
        smtp_is_configured=True,
        smtp_from_email="smarter@example.com",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_use_tls=True,
        smtp_username=SecretStr("user"),
        smtp_password=SecretStr("password"),
        email_admin="admin@example.com",
    )
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


class TestValidateMailList(InfrastructureTestBase):
    """Test EmailService.validate_mail_list()."""

    def test_valid_and_invalid(self):
        self.assertEqual(EmailService.validate_mail_list("a@example.com"), ["a@example.com"])
        self.assertEqual(EmailService.validate_mail_list(["a@example.com", "bad"]), ["a@example.com"])
        self.assertIsNone(EmailService.validate_mail_list(["bad"]))
        self.assertIsNone(EmailService.validate_mail_list(["bad"], quiet=True))
        self.assertIsNone(EmailService.validate_mail_list(42))  # type: ignore[arg-type]


class TestInMemoryEmailService(InfrastructureTestBase):
    """Test send_email(), with the in-memory email service."""

    def setUp(self):
        super().setUp()
        self.email = InMemoryEmailService()

    def test_send_email(self):
        events = self.capture(email_sent)
        self.assertTrue(self.email.send_email("Hello", "<p>Hi</p>", ["a@example.com", "bad"], html=True))
        self.assertEqual(len(self.email.outbox), 1)
        sent = self.email.outbox[0]
        self.assertEqual((sent.subject, sent.recipients), ("Hello", ["a@example.com"]))
        self.assertIn("Hi", sent.body)
        self.assertEqual(self.sent(events, email_sent)[0]["recipients"], ["a@example.com"])

    def test_from_email(self):
        self.email.send_email("Hello", "Hi", "a@example.com", from_email="support@example.com")
        self.assertEqual(self.email.outbox[0].sender, "support@example.com")

    def test_quiet_sends_nothing(self):
        self.assertFalse(self.email.send_email("Hello", "Hi", "a@example.com", quiet=True))
        self.assertEqual(self.email.outbox, [])

    def test_no_valid_recipient(self):
        self.assertFalse(self.email.send_email("Hello", "Hi", ["bad"]))
        self.assertEqual(self.email.outbox, [])

    def test_not_ready(self):
        email = InMemoryEmailService(ready=False)
        self.assertFalse(email.send_email("Hello", "Hi", "a@example.com"))
        self.assertFalse(email.send_email("Hello", "Hi", "a@example.com", quiet=True))
        self.assertEqual(email.outbox, [])

    def test_failure_is_not_raised(self):
        """A failure to deliver is announced, and logged, rather than raised."""
        events = self.capture(email_failed)
        self.email.fail = "mailbox full"
        self.assertFalse(self.email.send_email("Hello", "Hi", "a@example.com"))
        self.assertIn("mailbox full", self.sent(events, email_failed)[0]["error"])

    def test_system_exit_is_raised(self):
        with patch.object(self.email, "_deliver", side_effect=SystemExit):
            with self.assertRaises(SystemExit):
                self.email.send_email("Hello", "Hi", "a@example.com")


class TestSMTPEmailService(InfrastructureTestBase):
    """Test SMTPEmailService, with a fake SMTP class."""

    def setUp(self):
        super().setUp()
        self.smtp_class = MagicMock(spec=smtplib.SMTP)
        self.server = self.smtp_class.return_value.__enter__.return_value
        self.email = SMTPEmailService(allow_in_tests=True, smtp_class=self.smtp_class)

    def test_send_email(self):
        with patch(f"{MODULE}.smarter_settings", smtp_settings()):
            self.assertTrue(self.email.send_email("Hello", "Hi", ["a@example.com", "b@example.com"]))
        self.smtp_class.assert_called_once_with("smtp.example.com", 587)
        self.server.starttls.assert_called_once()
        self.server.login.assert_called_once_with("user", "password")
        sender, recipients, message = self.server.sendmail.call_args.args
        self.assertEqual(sender, "smarter@example.com")
        # each recipient is a recipient, rather than one comma-separated string, and the admin's
        # blind copy is on the envelope, but not in the message, where the recipients would see it.
        self.assertEqual(recipients, ["a@example.com", "b@example.com", "admin@example.com"])
        self.assertIn("Subject: Hello", message)
        self.assertNotIn("Bcc", message)
        self.assertNotIn("admin@example.com", message)

    def test_without_admin_bcc(self):
        """An email with a secret, e.g. a password reset link, has no blind copy."""
        with patch(f"{MODULE}.smarter_settings", smtp_settings()):
            self.assertTrue(self.email.send_email("Reset", "secret link", "a@example.com", bcc_admin=False))
        self.assertEqual(self.server.sendmail.call_args.args[1], ["a@example.com"])

    def test_without_tls(self):
        with patch(f"{MODULE}.smarter_settings", smtp_settings(smtp_use_tls=False, email_admin=None)):
            self.assertTrue(self.email.send_email("Hello", "Hi", "a@example.com"))
        self.server.starttls.assert_not_called()

    def test_smtp_error(self):
        self.server.sendmail.side_effect = smtplib.SMTPRecipientsRefused({})
        with patch(f"{MODULE}.smarter_settings", smtp_settings()):
            self.assertFalse(self.email.send_email("Hello", "Hi", "a@example.com"))

    def test_incomplete_configuration(self):
        for overrides in ({"smtp_from_email": None}, {"smtp_host": None}, {"smtp_password": None}):
            with self.subTest(**overrides), patch(f"{MODULE}.smarter_settings", smtp_settings(**overrides)):
                self.assertFalse(self.email.send_email("Hello", "Hi", "a@example.com"))
        self.server.sendmail.assert_not_called()

    def test_not_configured(self):
        with patch(f"{MODULE}.smarter_settings", smtp_settings(smtp_is_configured=False)):
            self.assertFalse(self.email.ready)
            self.assertFalse(self.email.send_email("Hello", "Hi", "a@example.com"))
        self.smtp_class.assert_not_called()

    def test_not_configured_logs_instructions(self):
        """Each email that is not sent, because SMTP is not configured, logs how to configure it."""
        with (
            patch(f"{MODULE}.smarter_settings", smtp_settings(smtp_is_configured=False)),
            patch(f"{MODULE}.logger") as logger,
        ):
            self.email.send_email("Welcome", "Hi", "a@example.com")
            self.email.send_email("Welcome", "Hi", "a@example.com")
            self.email.send_email("Quiet", "Hi", "a@example.com", quiet=True)
        self.assertEqual(logger.error.call_count, 2)
        banner = logger.error.call_args.args[0]
        self.assertIn("'Welcome' was not sent to: a@example.com", banner)
        self.assertIn("SMARTER_SMTP_USERNAME", banner)
        self.assertIn("SMARTER_SMTP_PASSWORD", banner)

    def test_nothing_is_sent_from_unit_tests(self):
        """By default, SMTP is not ready in the unit tests, so that tests never email real people."""
        email = SMTPEmailService(smtp_class=self.smtp_class)
        with patch(f"{MODULE}.smarter_settings", smtp_settings()):
            self.assertFalse(email.ready)
            self.assertFalse(email.send_email("Hello", "Hi", "a@example.com"))
        self.smtp_class.assert_not_called()

    def test_unit_tests_log_one_line(self):
        """In the unit tests, where email is never sent, an email that is not sent logs a one-line warning."""
        email = SMTPEmailService(smtp_class=self.smtp_class)
        with patch(f"{MODULE}.smarter_settings", smtp_settings()), patch(f"{MODULE}.logger") as logger:
            email.send_email("Hello", "Hi", "a@example.com")
        logger.error.assert_not_called()
        logger.warning.assert_called_once()


class TestAdminBcc(InfrastructureTestBase):
    """Test the blind copy to the platform's admin."""

    def test_admin_bcc(self):
        for email_admin, recipients, expected in (
            ("admin@example.com", ["a@example.com"], ["admin@example.com"]),
            ("Admin@Example.com", ["admin@example.com"], []),
            (None, ["a@example.com"], []),
            ("not an email", ["a@example.com"], []),
        ):
            with (
                self.subTest(email_admin=email_admin),
                patch(f"{MODULE}.smarter_settings", smtp_settings(email_admin=email_admin)),
            ):
                self.assertEqual(EmailService.admin_bcc(recipients), expected)

    def test_in_memory_bcc(self):
        email = InMemoryEmailService()
        with patch(f"{MODULE}.smarter_settings", smtp_settings()):
            email.send_email("Hello", "Hi", "a@example.com")
            email.send_email("Reset", "secret", "a@example.com", bcc_admin=False)
        self.assertEqual([sent.bcc for sent in email.outbox], [["admin@example.com"], []])
        self.assertNotIn("Bcc", email.outbox[0].headers)


class TestConfigureEmail(InfrastructureTestBase):
    def test_default_and_configured(self):
        self.assertIsInstance(get_email(), SMTPEmailService)
        self.assertIs(get_email(), get_email())
        fake = InMemoryEmailService()
        configure_email(lambda: fake)
        self.assertIs(get_email(), fake)
        self.assertIs(infrastructure.email, fake)
        configure_email(None)
        self.assertIsInstance(get_email(), SMTPEmailService)
