"""Test the MailchimpHelper class."""

from unittest.mock import patch

from mailchimp_marketing.api_client import ApiClientError

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..mailchimp_helpers import MailchimpHelper


class TestMailchimpHelper(SmarterTestBase):
    """Test the MailchimpHelper class."""

    @patch("smarter.common.helpers.mailchimp_helpers.MailchimpHelper.client")
    @patch("smarter.common.helpers.mailchimp_helpers.logger")
    def test_ping_success(self, mock_logger, mock_client):
        mock_client.ping.get.return_value = {"health_status": "Everything's Chimpy!"}
        helper = MailchimpHelper()
        result = helper.ping()
        self.assertTrue(result)
        mock_logger.info.assert_called()

    @patch("smarter.common.helpers.mailchimp_helpers.MailchimpHelper.client")
    @patch("smarter.common.helpers.mailchimp_helpers.logger")
    def test_ping_failure(self, mock_logger, mock_client):
        mock_client.ping.get.side_effect = ApiClientError({"status_code": 401, "text": "Unauthorized"})
        helper = MailchimpHelper()
        result = helper.ping()
        self.assertFalse(result)
        mock_logger.error.assert_called()

    @patch("smarter.common.helpers.mailchimp_helpers.MailchimpHelper.ping", return_value=True)
    @patch("smarter.common.helpers.mailchimp_helpers.MailchimpHelper.client")
    @patch("smarter.common.helpers.mailchimp_helpers.logger")
    def test_add_list_member_success(self, mock_logger, mock_client, mock_ping):
        mock_client.lists.add_list_member.return_value = {"status": "subscribed"}
        helper = MailchimpHelper()
        result = helper.add_list_member("test@example.com")
        self.assertTrue(result)
        mock_logger.info.assert_called()

    @patch("smarter.common.helpers.mailchimp_helpers.MailchimpHelper.ping", return_value=True)
    @patch("smarter.common.helpers.mailchimp_helpers.MailchimpHelper.client")
    @patch("smarter.common.helpers.mailchimp_helpers.logger")
    def test_add_list_member_failure(self, mock_logger, mock_client, mock_ping):
        mock_client.lists.add_list_member.return_value = {"status": "pending"}
        helper = MailchimpHelper()
        result = helper.add_list_member("test@example.com")
        self.assertFalse(result)
        mock_logger.warning.assert_called()

    @patch("smarter.common.helpers.mailchimp_helpers.MailchimpHelper.ping", return_value=True)
    @patch("smarter.common.helpers.mailchimp_helpers.MailchimpHelper.client")
    @patch("smarter.common.helpers.mailchimp_helpers.logger")
    def test_add_list_member_api_error(self, mock_logger, mock_client, mock_ping):

        mock_client.lists.add_list_member.side_effect = ApiClientError({"status_code": 400, "text": "Bad Request"})
        helper = MailchimpHelper()
        result = helper.add_list_member("test@example.com")
        self.assertFalse(result)
        self.assertTrue(mock_logger.error.called)

    @patch("smarter.common.helpers.mailchimp_helpers.MailchimpHelper.ping", return_value=False)
    @patch("smarter.common.helpers.mailchimp_helpers.logger")
    def test_add_list_member_ping_fail(self, mock_logger, mock_ping):
        helper = MailchimpHelper()
        result = helper.add_list_member("test@example.com")
        self.assertFalse(result)
        mock_logger.info.assert_not_called()
