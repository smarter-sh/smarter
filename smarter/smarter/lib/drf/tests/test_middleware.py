"""Test SmarterTokenAuthenticationMiddleware."""

from http import HTTPStatus
from logging import getLogger
from unittest.mock import MagicMock, Mock, patch

from django.http import HttpResponse
from django.test import Client, RequestFactory
from rest_framework.exceptions import AuthenticationFailed

from smarter.apps.account.tests.factories import (
    admin_user_factory,
    factory_account_teardown,
)
from smarter.lib.drf.middleware import SmarterTokenAuthenticationMiddleware
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.drf.token_authentication import SmarterTokenAuthenticationError
from smarter.lib.unittest.base_classes import SmarterTestBase


logger = getLogger(__name__)


class TestSmarterTokenAuthenticationMiddleware(SmarterTestBase):
    """Test SmarterTokenAuthenticationMiddleware."""

    def setUp(self) -> None:
        super().setUp()

        self.admin_user, self.account, self.user_profile = admin_user_factory()
        logger.info("TestSmarterTokenAuthenticationMiddleware() Setting up test class with name: %s", self.name)

        self.token_record, self.token_key = SmarterAuthToken.objects.create(
            name=self.name,
            user=self.admin_user,
            description="TestSmarterTokenAuthenticationMiddleware() test description",
        )  # type: ignore

        self.factory = RequestFactory()
        self.get_response = Mock(return_value=HttpResponse(status=HTTPStatus.OK))
        self.middleware = SmarterTokenAuthenticationMiddleware(self.get_response)

        self.request = self.factory.get("/")
        self.request.auth = None

    def tearDown(self) -> None:
        try:
            factory_account_teardown(user=self.admin_user, account=self.account, user_profile=self.user_profile)
            self.token_record.delete()
        except SmarterAuthToken.DoesNotExist:
            pass
        super().tearDown()

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

    @patch("smarter.lib.drf.middleware.SmarterTokenAuthentication")
    @patch("smarter.lib.drf.middleware.get_authorization_header")
    @patch("smarter.lib.drf.middleware.login")
    def test_call_successful_auth(self, mock_login, mock_get_auth_header, mock_auth_class):
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

    @patch("smarter.lib.drf.middleware.knox_settings")
    @patch("smarter.lib.drf.middleware.SmarterTokenAuthentication")
    @patch("smarter.lib.drf.middleware.SmarterJournaledJsonErrorResponse")
    @patch("smarter.lib.drf.middleware.logger")
    def test_call_authentication_failed(self, mock_logger, mock_error_response, mock_auth_class, mock_knox_settings):
        mock_knox_settings.AUTH_HEADER_PREFIX = b"Token"
        # Set up the middleware to treat this as a token auth request
        self.middleware.is_token_auth = Mock(return_value=True)
        self.request.auth = None
        # Set the header directly if your middleware uses it
        self.middleware.authorization_header = b"Token sometoken"

        mock_auth_instance = MagicMock()
        mock_auth_instance.authenticate.side_effect = AuthenticationFailed("fail")
        mock_auth_class.return_value = mock_auth_instance
        mock_error_response.return_value = "error_response"

        response = self.middleware(self.request)
        self.assertEqual(response, "error_response")
        mock_error_response.assert_called()
        mock_logger.warning.assert_called()
