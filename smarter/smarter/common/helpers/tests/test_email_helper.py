"""Test email helper functions."""

from unittest.mock import patch

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..email_helpers import EmailHelper, EmailHelperException


class TestEmailHelper(SmarterTestBase):
    """Test email helper functions."""

    @patch("smarter.common.helpers.email_helpers.SmarterValidator")
    def test_validate_mail_list_valid(self, mock_validator):
        mock_validator.is_valid_email.return_value = True
        emails = ["a@example.com", "b@example.com"]
        result = EmailHelper.validate_mail_list(emails)
        self.assertEqual(result, emails)

    @patch("smarter.common.helpers.email_helpers.SmarterValidator")
    @patch("smarter.common.helpers.email_helpers.logger")
    def test_validate_mail_list_invalid(self, mock_logger, mock_validator):
        mock_validator.is_valid_email.side_effect = [True, False]
        emails = ["a@example.com", "bad"]
        result = EmailHelper.validate_mail_list(emails)
        self.assertEqual(result, ["a@example.com"])
        mock_logger.warning.assert_called()

    @patch("smarter.common.helpers.email_helpers.SmarterValidator")
    @patch("smarter.common.helpers.email_helpers.logger")
    def test_validate_mail_list_none(self, mock_logger, mock_validator):
        mock_validator.is_valid_email.return_value = False
        emails = ["bad"]
        result = EmailHelper.validate_mail_list(emails)
        self.assertIsNone(result)
        mock_logger.warning.assert_called()

    @patch("smarter.common.helpers.email_helpers.EmailHelper.validate_mail_list", return_value=["a@example.com"])
    @patch("smarter.common.helpers.email_helpers.settings")
    @patch("smarter.common.helpers.email_helpers.smtplib.SMTP")
    @patch("smarter.common.helpers.email_helpers.logger")
    def test_send_email_success(self, mock_logger, mock_smtp, mock_settings, mock_validate):
        mock_settings.SMTP_FROM_EMAIL = "from@example.com"
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USE_TLS = True
        mock_settings.SMTP_USERNAME = "user"
        mock_settings.SMTP_PASSWORD = "pass"
        mock_settings.SMARTER_EMAIL_ADMIN = "admin@example.com"
        smtp_instance = mock_smtp.return_value.__enter__.return_value
        EmailHelper.send_email("subject", "body", ["a@example.com"])
        smtp_instance.starttls.assert_called()
        smtp_instance.login.assert_called_with("user", "pass")
        smtp_instance.sendmail.assert_called()
        mock_logger.info.assert_called()

    @patch("smarter.common.helpers.email_helpers.EmailHelper.validate_mail_list", return_value=None)
    @patch("smarter.common.helpers.email_helpers.logger")
    def test_send_email_no_valid(self, mock_logger, mock_validate):
        EmailHelper.send_email("subject", "body", ["bad@example.com"])
        mock_logger.info.assert_not_called()

    @patch("smarter.common.helpers.email_helpers.EmailHelper.validate_mail_list", return_value=["a@example.com"])
    @patch("smarter.common.helpers.email_helpers.settings")
    @patch("smarter.common.helpers.email_helpers.smtplib.SMTP")
    @patch("smarter.common.helpers.email_helpers.logger")
    def test_send_email_smtp_error(self, mock_logger, mock_smtp, mock_settings, mock_validate):
        mock_settings.SMTP_FROM_EMAIL = "from@example.com"
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USE_TLS = True
        mock_settings.SMTP_USERNAME = "user"
        mock_settings.SMTP_PASSWORD = "pass"
        mock_settings.SMARTER_EMAIL_ADMIN = "admin@example.com"
        smtp_instance = mock_smtp.return_value.__enter__.return_value
        smtp_instance.sendmail.side_effect = Exception("fail")
        with self.assertRaises(EmailHelperException):
            EmailHelper.send_email("subject", "body", ["a@example.com"])
