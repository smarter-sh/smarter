"""Test SmarterTokenAuthentication's inactive tokens and get_user_from_request()."""

from django.test import RequestFactory
from rest_framework.exceptions import AuthenticationFailed

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.lib.drf.token_authentication import (
    SmarterAnonymousUser,
    SmarterTokenAuthentication,
)


class TestSmarterTokenAuthenticationMore(ApiV1TestBase):
    """Test that an inactive token is refused, and that a request's user is found by its token."""

    def request(self, authorization=None):
        headers = {"HTTP_AUTHORIZATION": authorization} if authorization else {}
        return RequestFactory().get("/api/v1/", **headers)

    def test_inactive_token(self):
        self.token_record.deactivate()
        with self.assertRaises(AuthenticationFailed):
            SmarterTokenAuthentication().authenticate_credentials(self.token_key.encode())

    def test_invalid_token(self):
        with self.assertRaises(AuthenticationFailed):
            SmarterTokenAuthentication().authenticate_credentials(b"not-a-valid-token")

    def test_get_user_from_request(self):
        """Test that a request's user is found by its token, unless the token is inactive."""
        user = SmarterTokenAuthentication.get_user_from_request(self.request(f"Token {self.token_key}"))
        self.assertEqual(user, self.admin_user)
        self.token_record.deactivate()
        user = SmarterTokenAuthentication.get_user_from_request(self.request(f"Token {self.token_key}"))
        self.assertIsInstance(user, SmarterAnonymousUser)

    def test_get_user_from_request_anonymous(self):
        """Test that a request without a valid token is anonymous."""
        for authorization in (None, "Bearer abc", "Token not-a-token-key"):
            with self.subTest(authorization=authorization):
                user = SmarterTokenAuthentication.get_user_from_request(self.request(authorization))
                self.assertIsInstance(user, SmarterAnonymousUser)
