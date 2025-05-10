"""Test SmarterTokenAuthenticationMiddleware."""

from http import HTTPStatus
from unittest.mock import patch

from django.http import HttpResponse
from django.test import Client, RequestFactory

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
