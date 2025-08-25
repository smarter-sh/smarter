"""Test SmarterTokenAuthentication class"""

import time

from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

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

    def test_authenticate_credentials_inactive_token(self):
        self.smarter_auth_token.is_active = False
        self.smarter_auth_token.save()
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate_credentials(self.token_key[:1])

    def test_smarter_token_authentication_error_message(self):
        err = SmarterTokenAuthenticationError()
        self.assertEqual(err.get_formatted_err_message, "Smarter Token Authentication error")
