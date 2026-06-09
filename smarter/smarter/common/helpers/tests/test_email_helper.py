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

    def test_send_email_success(self):
        """Test sending an email successfully."""
        EmailHelper.send_email("subject", "body", ["a@example.com"])

    @patch("smarter.common.helpers.email_helpers.EmailHelper.validate_mail_list", return_value=None)
    @patch("smarter.common.helpers.email_helpers.logger")
    def test_send_email_no_valid(self, mock_logger, mock_validate):
        EmailHelper.send_email("subject", "body", ["bad@example.com"])
        mock_logger.info.assert_not_called()
