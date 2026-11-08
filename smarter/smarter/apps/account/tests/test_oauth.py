# pylint: disable=W0613
"""Test smarter.apps.account.oauth: whether the console offers sign-in with Google and with GitHub."""

from unittest.mock import patch

from smarter.apps.account.oauth import github_oauth_enabled, google_oauth_enabled
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestOAuthProviders(SmarterTestBase):
    """Each provider is offered only with the switch, its key and secret, and one of its backends."""

    @patch("smarter.apps.account.oauth.logger")
    @patch("smarter.apps.account.oauth.smarter_settings")
    @patch("smarter.apps.account.oauth.settings")
    @patch("smarter.apps.account.oauth.waffle.switch_is_active", return_value=True)
    def test_is_google_oauth_enabled_key_missing(self, mock_switch, mock_settings, mock_smarter_settings, mock_logger):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = ""
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = "secret"
        self.assertFalse(google_oauth_enabled(), "Expected is_google_oauth_enabled to be False when key is missing.")
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.oauth.logger")
    @patch("smarter.apps.account.oauth.smarter_settings")
    @patch("smarter.apps.account.oauth.settings")
    @patch("smarter.apps.account.oauth.waffle.switch_is_active", return_value=True)
    def test_is_google_oauth_enabled_secret_missing(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = ""
        self.assertFalse(google_oauth_enabled(), "Expected is_google_oauth_enabled to be False when secret is missing.")
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.oauth.logger")
    @patch("smarter.apps.account.oauth.smarter_settings")
    @patch("smarter.apps.account.oauth.settings")
    @patch("smarter.apps.account.oauth.waffle.switch_is_active", return_value=True)
    def test_is_google_oauth_enabled_key_missing_default_missing_value(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = "MISSING"
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = "secret"
        mock_smarter_settings.default_missing_value = "MISSING"
        self.assertFalse(
            google_oauth_enabled(),
            "Expected is_google_oauth_enabled to be False when key is missing and default_missing_value is set.",
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.oauth.logger")
    @patch("smarter.apps.account.oauth.smarter_settings")
    @patch("smarter.apps.account.oauth.settings")
    @patch("smarter.apps.account.oauth.waffle.switch_is_active", return_value=True)
    def test_is_google_oauth_enabled_secret_missing_default_missing_value(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = "MISSING"
        mock_smarter_settings.default_missing_value = "MISSING"
        self.assertFalse(
            google_oauth_enabled(),
            "Expected is_google_oauth_enabled to be False when secret is missing and default_missing_value is set.",
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.oauth.logger")
    @patch("smarter.apps.account.oauth.smarter_settings")
    @patch("smarter.apps.account.oauth.settings")
    @patch("smarter.apps.account.oauth.waffle.switch_is_active", return_value=True)
    def test_is_google_oauth_enabled_backend_found(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = "secret"
        mock_settings.AUTHENTICATION_BACKENDS = [
            "social_core.backends.google.GoogleOAuth2",
            "other.backend",
        ]
        self.assertTrue(google_oauth_enabled(), "Expected is_google_oauth_enabled to be True when backend is found.")

    @patch("smarter.apps.account.oauth.logger")
    @patch("smarter.apps.account.oauth.smarter_settings")
    @patch("smarter.apps.account.oauth.settings")
    @patch("smarter.apps.account.oauth.waffle.switch_is_active", return_value=True)
    def test_is_google_oauth_enabled_backend_not_found(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = "secret"
        mock_settings.AUTHENTICATION_BACKENDS = [
            "other.backend",
        ]
        self.assertFalse(
            google_oauth_enabled(), "Expected is_google_oauth_enabled to be False when backend is not found."
        )
        mock_logger.warning.assert_called()

    @patch("smarter.apps.account.oauth.logger")
    @patch("smarter.apps.account.oauth.smarter_settings")
    @patch("smarter.apps.account.oauth.settings")
    @patch("smarter.apps.account.oauth.waffle.switch_is_active", return_value=True)
    def test_is_github_oauth_enabled_key_missing(self, mock_switch, mock_settings, mock_smarter_settings, mock_logger):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = ""
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = "secret"
        self.assertFalse(github_oauth_enabled(), "Expected is_github_oauth_enabled to be False when key is missing.")
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.oauth.logger")
    @patch("smarter.apps.account.oauth.smarter_settings")
    @patch("smarter.apps.account.oauth.settings")
    @patch("smarter.apps.account.oauth.waffle.switch_is_active", return_value=True)
    def test_is_github_oauth_enabled_secret_missing(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = ""
        self.assertFalse(github_oauth_enabled(), "Expected is_github_oauth_enabled to be False when secret is missing.")
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.oauth.logger")
    @patch("smarter.apps.account.oauth.smarter_settings")
    @patch("smarter.apps.account.oauth.settings")
    def test_is_github_oauth_enabled_key_missing_default_missing_value(
        self, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = "MISSING"
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = "secret"
        mock_smarter_settings.default_missing_value = "MISSING"
        self.assertFalse(
            github_oauth_enabled(),
            "Expected is_github_oauth_enabled to be False when key is missing and default_missing_value is set.",
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.oauth.logger")
    @patch("smarter.apps.account.oauth.smarter_settings")
    @patch("smarter.apps.account.oauth.settings")
    def test_is_github_oauth_enabled_secret_missing_default_missing_value(
        self, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = "MISSING"
        mock_smarter_settings.default_missing_value = "MISSING"
        self.assertFalse(
            github_oauth_enabled(),
            "Expected is_github_oauth_enabled to be False when secret is missing and default_missing_value is set.",
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.oauth.logger")
    @patch("smarter.apps.account.oauth.smarter_settings")
    @patch("smarter.apps.account.oauth.settings")
    @patch("smarter.apps.account.oauth.waffle.switch_is_active", return_value=True)
    def test_is_github_oauth_enabled_backend_found(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = "secret"
        mock_settings.AUTHENTICATION_BACKENDS = [
            "social_core.backends.github.GithubOAuth2",
            "other.backend",
        ]
        self.assertTrue(github_oauth_enabled(), "Expected is_github_oauth_enabled to be True when backend is found.")

    @patch("smarter.apps.account.oauth.logger")
    @patch("smarter.apps.account.oauth.smarter_settings")
    @patch("smarter.apps.account.oauth.settings")
    @patch("smarter.apps.account.oauth.waffle.switch_is_active", return_value=True)
    def test_is_github_oauth_enabled_backend_not_found(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = "secret"
        mock_settings.AUTHENTICATION_BACKENDS = [
            "other.backend",
        ]
        self.assertFalse(
            github_oauth_enabled(), "Expected is_github_oauth_enabled to be False when backend is not found."
        )
        mock_logger.warning.assert_called()
