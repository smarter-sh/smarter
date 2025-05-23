"""Test SmarterTokenAuthentication class"""

from unittest.mock import Mock, patch

from rest_framework.exceptions import AuthenticationFailed

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..token_authentication import (
    SmarterTokenAuthentication,
    SmarterTokenAuthenticationError,
)


class TestSmarterTokenAuthentication(SmarterTestBase):
    """Test the SmarterTokenAuthentication class."""

    def setUp(self):
        super().setUp()
        self.auth = SmarterTokenAuthentication()
        self.token = b"sometoken"
        self.user = Mock()
        self.auth_token = Mock()
        self.smarter_auth_token = Mock()

    @patch("smarter.lib.drf.token_authentication.SmarterAuthToken")
    @patch("smarter.lib.drf.token_authentication.TokenAuthentication.authenticate_credentials")
    def test_authenticate_credentials_active_token(self, mock_super_auth, mock_token_model):
        # Mock super().authenticate_credentials to return user and token
        mock_super_auth.return_value = (self.user, self.auth_token)
        self.auth_token.token_key = "key123"
        # Mock SmarterAuthToken.objects.get to return an active token
        mock_token_model.objects.get.return_value = self.smarter_auth_token
        self.smarter_auth_token.is_active = True

        result = self.auth.authenticate_credentials(self.token)
        self.assertEqual(result, (self.user, self.smarter_auth_token))
        self.assertTrue(self.smarter_auth_token.last_used_at)
        self.smarter_auth_token.save.assert_called_once()

    @patch("smarter.lib.drf.token_authentication.SmarterAuthToken")
    @patch("smarter.lib.drf.token_authentication.TokenAuthentication.authenticate_credentials")
    def test_authenticate_credentials_inactive_token(self, mock_super_auth, mock_token_model):
        mock_super_auth.return_value = (self.user, self.auth_token)
        self.auth_token.token_key = "key123"
        mock_token_model.objects.get.return_value = self.smarter_auth_token
        self.smarter_auth_token.is_active = False

        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate_credentials(self.token)

    def test_smarter_token_authentication_error_message(self):
        err = SmarterTokenAuthenticationError()
        self.assertEqual(err.get_formatted_err_message, "Smarter Token Authentication error")
