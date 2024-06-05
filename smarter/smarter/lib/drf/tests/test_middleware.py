"""Test SmarterTokenAuthenticationMiddleware."""

import unittest
from http import HTTPStatus
from unittest.mock import patch

from django.http import HttpResponse
from django.test import Client, RequestFactory

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.tests.factories import admin_user_factory
from smarter.lib.django.user import User
from smarter.lib.drf.middleware import SmarterTokenAuthenticationMiddleware
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.drf.token_authentication import SmarterTokenAuthenticationError


class TestSmarterTokenAuthenticationMiddleware(unittest.TestCase, AccountMixin):
    """Test SmarterTokenAuthenticationMiddleware."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._user, cls._account, cls._user_profile = admin_user_factory()

        instance = cls()

        cls.token_record, cls.token_key = SmarterAuthToken.objects.create(
            name=instance.user.username,
            user=instance.user,
            description=instance.user.username,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        instance = cls()
        try:
            instance.user_profile.delete()
        except UserProfile.DoesNotExist:
            pass
        try:
            instance.user.delete()
        except User.DoesNotExist:
            pass
        try:
            instance.account.delete()
        except Account.DoesNotExist:
            pass
        try:
            instance.token_record.delete()
        except SmarterAuthToken.DoesNotExist:
            pass

    def setUp(self):
        self.middleware = SmarterTokenAuthenticationMiddleware(lambda req: HttpResponse())
        self.factory = RequestFactory()

    def test_valid_token_authorization_header(self):
        """Test that the middleware authenticates a valid today."""
        client = Client()
        headers = {"HTTP_AUTHORIZATION": f"Token {self.token_key}"}

        response = client.get(path="/", data=None, content_type="application/json", **headers)
        self.assertEqual(response.status_code, HTTPStatus.OK)

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
