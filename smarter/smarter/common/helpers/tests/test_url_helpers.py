"""Test URL helper functions."""

from unittest.mock import patch

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..url_helpers import clean_url, session_key_from_url


class TestUrlHelpers(SmarterTestBase):
    """Test URL helper functions."""

    def test_clean_url_removes_query(self):
        url = "https://example.com/path?foo=bar&baz=qux"
        cleaned = clean_url(url)
        self.assertEqual(cleaned, "https://example.com/path")

    def test_clean_url_no_query(self):
        url = "https://example.com/path"
        cleaned = clean_url(url)
        self.assertEqual(cleaned, url)

    @patch("smarter.common.helpers.url_helpers.SmarterValidator")
    @patch("smarter.common.helpers.url_helpers.SMARTER_CHAT_SESSION_KEY_NAME", "sessionid")
    def test_session_key_from_url_with_key(self, mock_validator):
        url = "https://example.com/path?sessionid=abc123&foo=bar"
        result = session_key_from_url(url)
        mock_validator.validate_url.assert_called_with(url)
        self.assertEqual(result, "abc123")

    @patch("smarter.common.helpers.url_helpers.SmarterValidator")
    @patch("smarter.common.helpers.url_helpers.SMARTER_CHAT_SESSION_KEY_NAME", "sessionid")
    def test_session_key_from_url_no_key(self, mock_validator):
        url = "https://example.com/path?foo=bar"
        result = session_key_from_url(url)
        mock_validator.validate_url.assert_called_with(url)
        self.assertIsNone(result)

    @patch("smarter.common.helpers.url_helpers.SmarterValidator")
    def test_session_key_from_url_empty(self, mock_validator):
        self.assertIsNone(session_key_from_url(""))
        mock_validator.validate_url.assert_not_called()
