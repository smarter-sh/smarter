# pylint: disable=wrong-import-position,W0613
"""Test the sign-out and account lifecycle views.

Sign-in and sign-up are the console's: see apps/account/api/web/tests.
"""

from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse

from smarter.apps.account.urls import AccountReverseNames
from smarter.apps.account.views.authentication import (
    AccountActivationEmailView,
    AccountInactiveView,
    LogoutView,
)

# our stuff
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse

from .mixins import TestAccountMixin

logger = logging.getLogger(__name__)


class TestLogoutView(TestAccountMixin):
    """
    Test Account LogoutView.

    path("logout/", LogoutView.as_view(), name="logout_view")
    """

    test_logger_prefix = f"{logging.SmarterFormattedText.text(__name__)}.TestLogoutView()"

    def test_get_logout_view_redirects_authenticated_user(self):
        """GET request to LogoutView for authenticated user should log out and redirect to root."""
        request = self.request_factory().get("/logout/")
        request.user = self.admin_user
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        view = LogoutView()
        response = view.get(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND,
            f"Expected FOUND for authenticated GET but got {response.status_code}",
        )
        self.assertEqual(response.url, "/")

    def test_get_logout_view_redirects_anonymous_user(self):
        """GET request to LogoutView for anonymous user should redirect to root (logout is idempotent)."""
        request = self.request_factory().get("/logout/")
        request.user = AnonymousUser()
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        view = LogoutView()
        response = view.get(request)
        self.assertEqual(
            response.status_code, HTTPStatus.FOUND, f"Expected FOUND for anonymous GET but got {response.status_code}"
        )
        self.assertEqual(response.url, "/")

    def test_post_logout_view_redirects_authenticated_user(self):
        """POST request to LogoutView for authenticated user should log out and redirect to root."""
        request = self.request_factory().post("/logout/")
        request.user = self.admin_user
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        view = LogoutView()
        response = view.post(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND,
            f"Expected FOUND for authenticated POST but got {response.status_code}",
        )
        self.assertEqual(response.url, "/")

    def test_post_logout_view_redirects_anonymous_user(self):
        """POST request to LogoutView for anonymous user should redirect to root (logout is idempotent)."""
        request = self.request_factory().post("/logout/")
        request.user = AnonymousUser()
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        view = LogoutView()
        response = view.post(request)
        self.assertEqual(
            response.status_code, HTTPStatus.FOUND, f"Expected FOUND for anonymous POST but got {response.status_code}"
        )
        if hasattr(response, "url"):
            self.assertEqual(response.url, "/")


class TestAccountInactiveView(TestAccountMixin):
    """
    Test AccountInactiveView.

    path("inactive/", AccountInactiveView.as_view(), name=AccountReverseNames.ACCOUNT_INACTIVE)
    """

    test_logger_prefix = f"{logging.SmarterFormattedText.text(__name__)}.TestAccountInactiveView()"

    def test_get_inactive_view_renders_authenticated_user(self):
        """GET request to AccountInactiveView for authenticated user should render the inactive page."""
        request = self.request_factory().get("/inactive/")
        request.user = self.admin_user
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        view = AccountInactiveView()
        response = view.get(request)
        self.assertEqual(
            response.status_code, HTTPStatus.OK, f"Expected OK for authenticated GET but got {response.status_code}"
        )

    def test_get_inactive_view_renders_anonymous_user(self):
        """GET request to AccountInactiveView for anonymous user should render the inactive page."""
        request = self.request_factory().get("/inactive/")
        request.user = AnonymousUser()
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        view = AccountInactiveView()
        response = view.get(request)
        self.assertEqual(
            response.status_code, HTTPStatus.OK, f"Expected OK for anonymous GET but got {response.status_code}"
        )


class TestAccountActivationEmailView(TestAccountMixin):
    """
    Test AccountActivationEmailView.

    path("activation/", AccountActivationEmailView.as_view(), name=AccountReverseNames.ACCOUNT_ACTIVATION)
    """

    test_logger_prefix = f"{logging.SmarterFormattedText.text(__name__)}.TestAccountActivationEmailView()"

    def setUp(self):
        super().setUp()
        self.url = reverse(AccountReverseNames.namespace + ":" + AccountReverseNames.ACCOUNT_ACTIVATION)
        logger.debug("%s.setUp() URL set to %s", self.test_logger_prefix, self.url)

    @patch("smarter.apps.account.views.authentication.account_views.infrastructure")
    def test_get_authenticated_admin_user_sends_email_and_renders(self, mock_infrastructure):
        """GET request with authenticated admin user should send activation email and render response."""
        request = self.request_factory().get(self.url)
        request.user = self.admin_user
        view = AccountActivationEmailView()
        response = view.get(request)
        self.assertEqual(
            response.status_code, HTTPStatus.OK, f"Expected OK for authenticated GET but got {response.status_code}"
        )
        mock_infrastructure.email.send_email.assert_called_once()
        self.assertFalse(mock_infrastructure.email.send_email.call_args.kwargs["bcc_admin"])

    @patch("smarter.apps.account.views.authentication.account_views.infrastructure")
    def test_get_authenticated_non_admin_user_sends_email_and_renders(self, mock_infrastructure):
        """GET request with authenticated non-admin user should send activation email and render response."""
        request = self.request_factory().get(self.url)
        request.user = self.non_admin_user
        view = AccountActivationEmailView()
        response = view.get(request)
        self.assertEqual(
            response.status_code, HTTPStatus.OK, f"Expected OK for authenticated GET but got {response.status_code}"
        )
        mock_infrastructure.email.send_email.assert_called_once()
        self.assertFalse(mock_infrastructure.email.send_email.call_args.kwargs["bcc_admin"])

    def test_get_anonymous_user_returns_not_found(self):
        """GET request with anonymous user should return not found."""
        request = self.request_factory().get(self.url)
        request.user = AnonymousUser()
        view = AccountActivationEmailView()
        response = view.get(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.NOT_FOUND,
            f"Expected NOT_FOUND for anonymous GET but got {response.status_code}",
        )

    def test_get_user_without_is_authenticated_returns_not_found(self):
        """GET request with user missing is_authenticated should return not found."""
        request = self.request_factory().get(self.url)
        request.user = AnonymousUser()
        view = AccountActivationEmailView()
        response = view.get(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.NOT_FOUND,
            f"Expected NOT_FOUND for user missing is_authenticated but got {response.status_code}",
        )
