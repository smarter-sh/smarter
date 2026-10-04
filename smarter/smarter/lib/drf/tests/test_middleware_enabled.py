"""
Test SmarterTokenAuthenticationMiddleware with its waffle switch on.

The middleware does nothing while ENABLE_MIDDLEWARE_SMARTER_TOKEN_AUTH is off,
so these tests turn the switch on, and authenticate requests with real tokens.
"""

import asyncio
from datetime import timedelta
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory
from django.utils import timezone

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.middleware import SmarterTokenAuthenticationMiddleware
from smarter.lib.drf.token_authentication import SmarterAnonymousUser

MODULE = "smarter.lib.drf.middleware"
API_PATH = "/api/v1/cli/whoami/"


class TestSmarterTokenAuthenticationMiddlewareEnabled(ApiV1TestBase):
    """Test the middleware's token authentication, with the switch on."""

    def setUp(self):
        super().setUp()
        original = waffle.switch_is_active
        patcher = patch(
            "smarter.lib.django.waffle.switch_is_active",
            side_effect=lambda name: name == SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SMARTER_TOKEN_AUTH
            or original(name),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.middleware = SmarterTokenAuthenticationMiddleware(lambda request: HttpResponse("ok"))
        self.factory = RequestFactory()

    def request(self, path: str = API_PATH, authorization: str | None = None):
        headers = {"HTTP_HOST": "localhost:9357"}
        if authorization is not None:
            headers["HTTP_AUTHORIZATION"] = authorization
        request = self.factory.post(path, **headers)
        SessionMiddleware(lambda r: None).process_request(request)  # type: ignore[arg-type]
        return request

    def test_valid_token(self):
        """Test that a valid token logs in its user."""
        request = self.request(authorization=f"Token {self.token_key}")
        with patch(f"{MODULE}.smarter_token_authentication_success") as success:
            response = self.middleware(request)
        self.assertEqual(response.content, b"ok")
        self.assertEqual(request.user, self.admin_user)
        success.send.assert_called_once()

    def test_invalid_token(self):
        """Test that an invalid token returns a 401, without calling the view."""
        with patch(f"{MODULE}.smarter_token_authentication_failure") as failure:
            response = self.middleware(self.request(authorization="Token not-a-valid-token"))
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        failure.send.assert_called_once()

    def test_requests_that_are_passed_through(self):
        """Test that non-api urls, and requests without a token, are passed to the view unauthenticated."""
        cases = [
            self.request("/dashboard/", authorization=f"Token {self.token_key}"),
            self.request(),
            self.request(authorization="Bearer abc"),
            self.request(authorization="Token"),
            self.request(authorization="Token a b"),
        ]
        for request in cases:
            with self.subTest(authorization=request.META.get("HTTP_AUTHORIZATION")):
                self.assertEqual(self.middleware(request).content, b"ok")

    def test_already_authenticated(self):
        request = self.request(authorization="Token not-a-valid-token")
        request.auth = "already"
        self.assertEqual(self.middleware(request).content, b"ok")

    def test_switch_off(self):
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=False):
            self.assertEqual(self.middleware(self.request(authorization="Token not-a-valid-token")).content, b"ok")

    def test_amnesty(self):
        self.assertEqual(self.middleware(self.request("/healthz/", authorization="Token x")).content, b"ok")

    def test_async(self):
        """Test that the async middleware authenticates, and returns the view's response, not its coroutine."""

        async def get_response(request):
            return HttpResponse("async ok")

        middleware = SmarterTokenAuthenticationMiddleware(get_response)
        request = self.request(authorization=f"Token {self.token_key}")
        response = asyncio.run(middleware(request))
        self.assertEqual(response.content, b"async ok")
        self.assertEqual(request.user, self.admin_user)

    def test_authenticate_request_errors(self):
        """Test that an authentication backend that returns no user is an authentication failure."""
        from rest_framework.exceptions import (  # pylint: disable=import-outside-toplevel
            AuthenticationFailed,
        )

        for result in (None, (None, "auth")):
            with (
                self.subTest(result=result),
                patch(f"{MODULE}.SmarterTokenAuthentication.authenticate", return_value=result),
            ):
                with self.assertRaises(AuthenticationFailed):
                    SmarterTokenAuthenticationMiddleware.authenticate_request(self.request())

    def test_validate_token_lifetime(self):
        """Test that an expired token, or a token that isn't found, is logged, and a missing digest is ignored."""
        with patch(f"{MODULE}.logger") as logger:
            self.middleware.validate_token_lifetime(user=self.admin_user, auth_obj=object())
            logger.warning.assert_not_called()
            self.middleware.validate_token_lifetime(user=self.admin_user, auth_obj=MagicMock(digest="not-a-digest"))
            self.assertEqual(logger.warning.call_count, 1)
            self.middleware.validate_token_lifetime(user=self.admin_user, auth_obj=self.token_record)
            self.assertEqual(logger.warning.call_count, 1)
            self.token_record.created = timezone.now() - timedelta(days=10000)
            self.token_record.save()
            self.middleware.validate_token_lifetime(user=self.admin_user, auth_obj=self.token_record)
            self.assertEqual(logger.warning.call_count, 2)

    def test_helpers(self):
        self.assertTrue(SmarterTokenAuthenticationMiddleware.is_api_request("http://localhost:9357/api/v1/"))
        self.assertEqual(SmarterTokenAuthenticationMiddleware.get_auth_prefix(), "Token")
        self.assertEqual(self.middleware.extract_token("token abc"), "abc")
        self.assertIsNone(self.middleware.extract_token(""))
        request = MagicMock(spec=["path"])
        self.assertIsInstance(
            SmarterTokenAuthenticationMiddleware.ensure_request_user(request).user, SmarterAnonymousUser
        )
        for header in (b"Token a", "Token a", memoryview(b"Token a"), 42):
            with self.subTest(header=header), patch(f"{MODULE}.get_authorization_header", return_value=header):
                self.assertEqual(
                    SmarterTokenAuthenticationMiddleware.get_authorization_header(self.request()),
                    "" if header == 42 else "Token a",
                )
