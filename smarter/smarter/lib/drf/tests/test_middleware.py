"""Test SmarterTokenAuthenticationMiddleware."""

from http import HTTPStatus
from unittest.mock import MagicMock, Mock, patch

from django.http import HttpResponse
from django.test import Client, RequestFactory
from rest_framework.exceptions import AuthenticationFailed

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.drf.middleware import SmarterTokenAuthenticationMiddleware
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.drf.token_authentication import SmarterTokenAuthenticationError


class TestSmarterTokenAuthenticationMiddleware(TestAccountMixin):
    """Test SmarterTokenAuthenticationMiddleware."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        instance = cls()

        cls.token_record, cls.token_key = SmarterAuthToken.objects.create(
            name=instance.admin_user.username,
            user=instance.admin_user,
            description=instance.admin_user.username,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        instance = cls()
        try:
            instance.token_record.delete()
        except SmarterAuthToken.DoesNotExist:
            pass

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.middleware = SmarterTokenAuthenticationMiddleware(lambda req: HttpResponse())
        self.factory = RequestFactory()
        self.get_response = Mock()
        self.request = Mock()
        self.request.build_absolute_uri.return_value = "http://testserver/api/"
        self.request.auth = None

    def test_valid_token_authorization_header(self):
        """Test that the middleware authenticates a valid today."""
        client = Client()
        headers = {"HTTP_AUTHORIZATION": f"Token {self.token_key}"}

        response = client.get(path="/", data=None, content_type="application/json", **headers)
        self.assertIn(response.status_code, [HTTPStatus.OK, HTTPStatus.FOUND, HTTPStatus.MOVED_PERMANENTLY])

    def test_no_authorization_header(self):
        """Test that the middleware does not prevent access to public urls."""
        request = self.factory.get("/")
        response = self.middleware(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    @patch("smarter.lib.drf.token_authentication.SmarterTokenAuthentication.authenticate")
    def test_invalid_token(self, mock_authenticate):
        """Test that the middleware raises an exception when the token is invalid."""
        mock_authenticate.side_effect = SmarterTokenAuthenticationError
        request = self.factory.get("/", HTTP_AUTHORIZATION="Token abc123")
        with self.assertRaises(SmarterTokenAuthenticationError):
            self.middleware(request)

    @patch("smarter.lib.drf.middleware.get_authorization_header")
    @patch("smarter.lib.drf.middleware.knox_settings")
    def test_is_token_auth_true(self, mock_knox_settings, mock_get_auth_header):
        mock_knox_settings.AUTH_HEADER_PREFIX = b"Token"
        self.middleware.authorization_header = b"Token sometoken"
        result = self.middleware.is_token_auth(self.request)
        self.assertTrue(result)

    @patch("smarter.lib.drf.middleware.get_authorization_header")
    @patch("smarter.lib.drf.middleware.knox_settings")
    def test_is_token_auth_false(self, mock_knox_settings, mock_get_auth_header):
        mock_knox_settings.AUTH_HEADER_PREFIX = b"Token"
        self.middleware.authorization_header = b"Bearer sometoken"
        result = self.middleware.is_token_auth(self.request)
        self.assertFalse(result)

    @patch("smarter.lib.drf.middleware.get_authorization_header")
    def test_call_not_token_auth(self, mock_get_auth_header):
        mock_get_auth_header.return_value = b"Bearer sometoken"
        self.middleware.is_token_auth = Mock(return_value=False)
        response = self.middleware(self.request)
        self.get_response.assert_called_with(self.request)
        self.assertEqual(response, self.get_response.return_value)

    @patch("smarter.lib.drf.middleware.get_authorization_header")
    def test_call_already_authenticated(self, mock_get_auth_header):
        mock_get_auth_header.return_value = b"Token sometoken"
        self.middleware.is_token_auth = Mock(return_value=True)
        self.request.auth = True
        response = self.middleware(self.request)
        self.get_response.assert_called_with(self.request)
        self.assertEqual(response, self.get_response.return_value)

    @patch("smarter.lib.drf.middleware.login")
    @patch("smarter.lib.drf.middleware.get_authorization_header")
    @patch("smarter.lib.drf.middleware.SmarterTokenAuthentication")
    def test_call_successful_auth(self, mock_auth_class, mock_get_auth_header, mock_login):
        mock_get_auth_header.return_value = b"Token sometoken"
        self.middleware.is_token_auth = Mock(return_value=True)
        self.request.auth = None
        mock_auth_instance = MagicMock()
        mock_auth_instance.authenticate.return_value = ("user", "token")
        mock_auth_class.return_value = mock_auth_instance

        response = self.middleware(self.request)
        self.assertEqual(response, self.get_response.return_value)
        self.assertEqual(self.request.user, "user")
        mock_login.assert_called_with(self.request, "user", backend="django.contrib.auth.backends.ModelBackend")

    @patch("smarter.lib.drf.middleware.logger")
    @patch("smarter.lib.drf.middleware.SmarterJournaledJsonErrorResponse")
    @patch("smarter.lib.drf.middleware.SmarterTokenAuthentication")
    @patch("smarter.lib.drf.middleware.get_authorization_header")
    def test_call_authentication_failed(self, mock_get_auth_header, mock_auth_class, mock_error_response, mock_logger):
        mock_get_auth_header.return_value = b"Token sometoken"
        self.middleware.is_token_auth = Mock(return_value=True)
        self.request.auth = None
        mock_auth_instance = MagicMock()
        mock_auth_instance.authenticate.side_effect = AuthenticationFailed("fail")
        mock_auth_class.return_value = mock_auth_instance
        mock_error_response.return_value = "error_response"

        response = self.middleware(self.request)
        self.assertEqual(response, "error_response")
        mock_error_response.assert_called()
        mock_logger.warning.assert_called()
