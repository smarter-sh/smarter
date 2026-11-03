"""Tests for smarter.apps.mcpserver.acting_user: the signed user of the platform's requests to its operations server."""

from unittest import mock
from urllib.parse import urlparse

from django.contrib.auth.models import AnonymousUser
from django.core import signing

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.mcpserver.acting_user import (
    ACTING_USER_HEADER,
    MAX_AGE_SECONDS,
    SALT,
    acting_user,
    acting_user_headers,
    current_acting_user,
    is_operations_server_url,
    operations_server_url,
    sign_acting_user,
    verify_acting_user,
)
from smarter.common.conf import smarter_settings

MODULE = "smarter.apps.mcpserver.acting_user"


class TestActingUser(TestAccountMixin):
    """Test signing, verifying and scoping the acting user."""

    def test_operations_server_url(self):
        url = operations_server_url()
        self.assertTrue(url.startswith(smarter_settings.environment_url))
        self.assertTrue(url.endswith("/api/v1/mcp/smarter-operations/"))

    def test_is_operations_server_url(self):
        """Only this platform's own operations server matches: scheme, host, port and path."""
        url = operations_server_url()
        self.assertTrue(is_operations_server_url(url))
        self.assertTrue(is_operations_server_url(url.rstrip("/")))
        host = urlparse(url).netloc
        self.assertTrue(is_operations_server_url(url.replace(host, host.upper(), 1)))
        others = [
            None,
            "",
            "https://evil.example.com/api/v1/mcp/smarter-operations/",
            url.replace("/smarter-operations/", "/smarter-project/"),
            url + "extra/",
        ]
        if url.startswith("https://"):
            others.append(url.replace("https://", "http://", 1))
        else:
            others.append(url.replace("http://", "https://", 1))
        for other in others:
            with self.subTest(url=other):
                self.assertFalse(is_operations_server_url(other))

    def test_sign_and_verify(self):
        for user, expected in ((self.admin_user, self.admin_user.pk), (None, None)):
            with self.subTest(user=user):
                verified = verify_acting_user(sign_acting_user(user))
                self.assertIsNotNone(verified)
                self.assertEqual(verified.user_id, expected)  # type: ignore[union-attr]

    def test_the_value_carries_no_name(self):
        """The header carries the user's id, not their name or email address."""
        value = sign_acting_user(self.admin_user)
        self.assertNotIn(self.admin_user.username, value)
        self.assertNotIn(self.admin_user.email, value)

    def test_refused(self):
        """A value that this platform did not sign, with this salt, for an ActingUser, is refused."""
        other_salt = signing.TimestampSigner(salt="something.else").sign_object({"user_id": self.admin_user.pk})
        not_an_acting_user = signing.TimestampSigner(salt=SALT).sign_object({"user": self.admin_user.pk})
        tampered = sign_acting_user(self.admin_user)[:-2] + "xx"
        cases = ["", "not signed", other_salt, not_an_acting_user, tampered]
        for value in cases:
            with self.subTest(value=value):
                self.assertIsNone(verify_acting_user(value))

    def test_expired(self):
        value = sign_acting_user(self.admin_user)
        with mock.patch("django.core.signing.time.time", return_value=10**10):
            self.assertIsNone(verify_acting_user(value))
        self.assertGreater(MAX_AGE_SECONDS, 0)

    def test_acting_user(self):
        """The block sets the acting user, and restores the one before it."""
        self.assertIsNone(current_acting_user())
        with acting_user(self.admin_user):
            self.assertEqual(current_acting_user(), self.admin_user)
            with acting_user(AnonymousUser()):
                self.assertIsNone(current_acting_user())
            self.assertEqual(current_acting_user(), self.admin_user)
        self.assertIsNone(current_acting_user())

    def test_headers(self):
        """Only this platform's operations server gets the header."""
        headers = acting_user_headers(operations_server_url(), self.admin_user)
        self.assertEqual(list(headers), [ACTING_USER_HEADER])
        self.assertEqual(verify_acting_user(headers[ACTING_USER_HEADER]).user_id, self.admin_user.pk)  # type: ignore[union-attr]
        self.assertEqual(acting_user_headers("https://mcp.example.com/mcp", self.admin_user), {})
        self.assertEqual(acting_user_headers(None, self.admin_user), {})
