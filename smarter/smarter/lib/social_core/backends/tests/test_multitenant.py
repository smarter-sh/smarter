"""
Test :mod:`smarter.lib.social_core.backends.multitenant`.

The subscription status api is never called: requests.get is mocked.
"""

from http import HTTPStatus
from unittest.mock import MagicMock, patch

from django.test import RequestFactory
from requests.exceptions import (
    HTTPError,
    RequestException,
    Timeout,
    TooManyRedirects,
)

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.const import SmarterEnvironments
from smarter.lib.social_core.backends.multitenant import (
    INACTIVE_ACCOUNT_REDIRECT_URL,
    DjangoModelBackendMultitenant,
    GithubOAuth2Multitenant,
    GoogleOAuth2Multitenant,
    subscription_status_code,
    verify_payment_status,
)

MODULE = "smarter.lib.social_core.backends.multitenant"


def verify(username: str) -> bool:
    """Call verify_payment_status() with the subscription status api's answer for the user uncached."""
    subscription_status_code.invalidate(username)
    return verify_payment_status(username)


class TestVerifyPaymentStatus(TestAccountMixin):
    """Test verify_payment_status(): superusers pass, and errors of the status api fail open."""

    def setUp(self):
        super().setUp()
        patcher = patch(f"{MODULE}.switch_is_active", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_superuser(self):
        with patch(f"{MODULE}.requests.get") as get:
            self.assertTrue(verify(self.admin_user.username))
        get.assert_not_called()

    def test_switch_off(self):
        with patch(f"{MODULE}.switch_is_active", return_value=False), patch(f"{MODULE}.requests.get") as get:
            self.assertTrue(verify(self.non_admin_user.username))
        get.assert_not_called()

    def test_status(self):
        for status, expected in ((HTTPStatus.OK, True), (HTTPStatus.PAYMENT_REQUIRED, False)):
            with (
                self.subTest(status=status),
                patch(f"{MODULE}.requests.get", return_value=MagicMock(status_code=status)) as get,
            ):
                self.assertEqual(verify(self.non_admin_user.username), expected)
            self.assertEqual(get.call_args.kwargs["headers"]["X-Client-Username"], self.non_admin_user.username)

    def test_server_errors_fail_open(self):
        """A 5xx of the status api is a failure, not an inactive subscription."""
        with patch(f"{MODULE}.requests.get", return_value=MagicMock(status_code=HTTPStatus.BAD_GATEWAY)):
            self.assertTrue(verify(self.non_admin_user.username))

    def test_a_failure_is_not_cached(self):
        """After a failure, the next sign-in asks the status api again."""
        username = self.non_admin_user.username
        subscription_status_code.invalidate(username)
        with patch(f"{MODULE}.requests.get", side_effect=Timeout()):
            self.assertTrue(verify_payment_status(username))
        with patch(f"{MODULE}.requests.get", return_value=MagicMock(status_code=HTTPStatus.PAYMENT_REQUIRED)) as get:
            self.assertFalse(verify_payment_status(username))
            self.assertFalse(verify_payment_status(username))
        get.assert_called_once()
        subscription_status_code.invalidate(username)

    def test_the_switch_is_never_cached(self):
        """Turning multitenant authentication off applies at once, whatever the status api answered before."""
        username = self.non_admin_user.username
        subscription_status_code.invalidate(username)
        with patch(f"{MODULE}.requests.get", return_value=MagicMock(status_code=HTTPStatus.PAYMENT_REQUIRED)):
            self.assertFalse(verify_payment_status(username))
        with patch(f"{MODULE}.switch_is_active", return_value=False):
            self.assertTrue(verify_payment_status(username))
        subscription_status_code.invalidate(username)

    def test_errors_fail_open(self):
        for error in (Timeout(), HTTPError(), ConnectionError(), TooManyRedirects(), RequestException(), ValueError()):
            with self.subTest(error=type(error).__name__), patch(f"{MODULE}.requests.get", side_effect=error):
                self.assertTrue(verify(self.non_admin_user.username))


class TestMultitenantBackends(TestAccountMixin):
    """Test that the backends return a user's details only while their subscription is active."""

    def backend(self, backend_class):
        strategy = MagicMock()
        strategy.request = RequestFactory().get("/")
        strategy.request.session = {}
        return backend_class(strategy=strategy)

    def test_oauth2_backends(self):
        details = {"username": "someone", "email": "someone@example.com"}
        for backend_class, parent in (
            (GoogleOAuth2Multitenant, "social_core.backends.google.GoogleOAuth2.get_user_details"),
            (GithubOAuth2Multitenant, "social_core.backends.github.GithubOAuth2.get_user_details"),
        ):
            with self.subTest(backend=backend_class.__name__):
                backend = self.backend(backend_class)
                with patch(parent, return_value=details):
                    with patch(f"{MODULE}.verify_payment_status", return_value=True):
                        self.assertEqual(backend.get_user_details({}), details)
                    with (
                        patch(f"{MODULE}.verify_payment_status", return_value=False),
                        patch(f"{MODULE}.messages"),
                        patch(f"{MODULE}.smarter_settings", MagicMock(environment=SmarterEnvironments.PROD)),
                    ):
                        self.assertIsNone(backend.get_user_details({}))
                    self.assertEqual(backend.strategy.request.session["account_status"], "inactive")
                with patch(parent, return_value=None):
                    self.assertIsNone(backend.get_user_details({}))
                with patch(parent, return_value="not a dict"):
                    self.assertEqual(backend.get_user_details({}), "not a dict")

    def test_github_local_environment(self):
        """Test that github logins aren't refused in a local environment."""
        backend = self.backend(GithubOAuth2Multitenant)
        details = {"username": "someone"}
        with (
            patch("social_core.backends.github.GithubOAuth2.get_user_details", return_value=details),
            patch(f"{MODULE}.verify_payment_status", return_value=False),
            patch(f"{MODULE}.smarter_settings", MagicMock(environment=SmarterEnvironments.LOCAL)),
        ):
            self.assertEqual(backend.get_user_details({}), details)

    def test_model_backend(self):
        """Test that a user whose subscription isn't active is redirected to the inactive account page."""
        backend = DjangoModelBackendMultitenant()
        request = RequestFactory().post("/")
        with patch("django.contrib.auth.backends.ModelBackend.authenticate", return_value=self.non_admin_user):
            with patch(f"{MODULE}.verify_payment_status", return_value=True) as verify_status:
                self.assertEqual(backend.authenticate(request, username="u", password="p"), self.non_admin_user)
            # the authenticated user's username, a string, whatever the caller passed as username.
            verify_status.assert_called_once_with(self.non_admin_user.get_username())
            with (
                patch(f"{MODULE}.verify_payment_status", return_value=False),
                patch(f"{MODULE}.messages") as messages,
                patch(f"{MODULE}.redirect", return_value="redirected") as redirect,
            ):
                self.assertEqual(backend.authenticate(request, username="u", password="p"), "redirected")
            redirect.assert_called_once_with(INACTIVE_ACCOUNT_REDIRECT_URL)
            messages.error.assert_called_once()
        with patch("django.contrib.auth.backends.ModelBackend.authenticate", return_value=None):
            self.assertIsNone(backend.authenticate(request, username="u", password="p"))

    def test_model_backend_inactive_redirect(self):
        """Test that a user whose subscription isn't active is redirected to the inactive account page."""
        request = RequestFactory().post("/")
        with (
            patch("django.contrib.auth.backends.ModelBackend.authenticate", return_value=self.non_admin_user),
            patch(f"{MODULE}.verify_payment_status", return_value=False),
            patch(f"{MODULE}.messages"),
        ):
            response = DjangoModelBackendMultitenant().authenticate(request, username="u", password="p")
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response["Location"], "/account/inactive/")
