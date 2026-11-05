"""Test SmarterTokenAuthentication class."""

import time
from unittest.mock import patch

from django.test import RequestFactory
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.drf.token_authentication import (
    SmarterTokenAuthentication,
    SmarterTokenAuthenticationError,
)


class TestSmarterTokenAuthentication(TestAccountMixin):
    """Test the SmarterTokenAuthentication class."""

    smarter_auth_token: SmarterAuthToken

    def setUp(self):
        super().setUp()
        self.auth = SmarterTokenAuthentication()
        self.smarter_auth_token, self.token_key = SmarterAuthToken.objects.create(
            user_profile=self.user_profile,
            name=self.name,
            user=self.admin_user,
            description="TestSmarterTokenAuthenticationMiddleware() test description",
        )  # type: ignore

    def tearDown(self):
        super().tearDown()
        self.smarter_auth_token.delete()

    def test_authenticate_credentials_active_token(self):
        start_time = timezone.now()
        token_key_bytes = self.token_key.encode()
        authenticated_user, self.smarter_auth_token = self.auth.authenticate_credentials(token_key_bytes)
        # Simulate some processing time to avoid a race condition with the
        # Django signal that updates last_used_at
        time.sleep(1)
        self.smarter_auth_token.refresh_from_db()
        self.assertTrue(authenticated_user.is_authenticated)
        self.assertTrue(self.smarter_auth_token.is_active)
        self.assertEqual((authenticated_user, self.smarter_auth_token), (self.admin_user, self.smarter_auth_token))
        self.assertLess(start_time, self.smarter_auth_token.last_used_at)

    def test_last_used_at_is_written_at_most_once_per_resolution(self):
        """A key used twice within LAST_USED_RESOLUTION is written once, not on every request."""
        token_key_bytes = self.token_key.encode()
        self.auth.authenticate_credentials(token_key_bytes)
        self.smarter_auth_token.refresh_from_db()
        first_use = self.smarter_auth_token.last_used_at
        self.assertIsNotNone(first_use)

        self.auth.authenticate_credentials(token_key_bytes)
        self.smarter_auth_token.refresh_from_db()
        self.assertEqual(self.smarter_auth_token.last_used_at, first_use)

    def test_authenticate_for_request_authenticates_once(self):
        """The same request's token is authenticated once, however many layers ask."""
        request = RequestFactory().get("/api/v1/cli/whoami/")
        token_key_bytes = self.token_key.encode()
        with patch.object(
            SmarterTokenAuthentication,
            "authenticate_credentials",
            return_value=(self.admin_user, self.smarter_auth_token),
        ) as authenticate_credentials:
            first = SmarterTokenAuthentication.authenticate_for_request(request, token_key_bytes)
            second = SmarterTokenAuthentication.authenticate_for_request(Request(request), token_key_bytes)
        authenticate_credentials.assert_called_once()
        self.assertEqual(first, second)

    def test_a_different_token_is_authenticated_again(self):
        request = RequestFactory().get("/api/v1/cli/whoami/")
        SmarterTokenAuthentication.authenticate_for_request(request, self.token_key.encode())
        with self.assertRaises(AuthenticationFailed):
            SmarterTokenAuthentication.authenticate_for_request(request, b"not-a-valid-token")

    def test_without_a_request_nothing_is_remembered(self):
        token_key_bytes = self.token_key.encode()
        with patch.object(
            SmarterTokenAuthentication,
            "authenticate_credentials",
            return_value=(self.admin_user, self.smarter_auth_token),
        ) as authenticate_credentials:
            SmarterTokenAuthentication.authenticate_for_request(None, token_key_bytes)
            SmarterTokenAuthentication.authenticate_for_request(None, token_key_bytes)
        self.assertEqual(authenticate_credentials.call_count, 2)

    def test_authenticate_remembers_the_header_token(self):
        """DRF's authenticate() keeps its result for the request's later checks."""
        request = RequestFactory().get("/api/v1/cli/whoami/", HTTP_AUTHORIZATION=f"Token {self.token_key}")
        user, _ = self.auth.authenticate(Request(request))
        self.assertEqual(user, self.admin_user)
        with patch.object(SmarterTokenAuthentication, "authenticate_credentials") as authenticate_credentials:
            again = self.auth.authenticate(request)
        authenticate_credentials.assert_not_called()
        self.assertEqual(again[0], self.admin_user)

    def test_authenticate_without_a_token_header(self):
        request = RequestFactory().get("/api/v1/cli/whoami/")
        self.assertIsNone(self.auth.authenticate(Request(request)))

    def test_authenticate_credentials_inactive_token(self):
        self.smarter_auth_token.is_active = False
        self.smarter_auth_token.save()
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate_credentials(self.token_key[:1])

    def test_smarter_token_authentication_error_message(self):
        err = SmarterTokenAuthenticationError()
        self.assertEqual(err.get_formatted_err_message, "Smarter Token Authentication error")
