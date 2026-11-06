# pylint: disable=wrong-import-position
"""Test the account app's urls, and that its retired urls are gone."""

from http import HTTPStatus

from django.test import Client
from django.urls import resolve
from django.urls import reverse as django_reverse

# our stuff
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.urls import AccountReverseNames
from smarter.apps.dashboard.views.console_app import ConsoleAppView
from smarter.lib.django.shortcuts import reverse
from smarter.urls.console import ConsoleReverseNames


class TestUrls(TestAccountMixin):
    """Test the account urls of the console urlconf."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client = Client()

    def tearDown(self):
        self.client.logout()
        super().tearDown()

    def verify_response(self, reverse_name: str, status_code: int):
        """Assert that GET of a named url returns status_code."""
        url = reverse(reverse_name)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status_code, url)

    def test_console_pages(self):
        """
        Sign-in, registration, password reset and the account's lifecycle pages are the single-page console's.

        See smarter.apps.dashboard.tests.test_console_app for the pages themselves.
        """
        for name in (
            ConsoleReverseNames.login_view,
            ConsoleReverseNames.register_view,
            "account_password_reset_request",
            f"{AccountReverseNames.namespace}:{AccountReverseNames.ACCOUNT_INACTIVE}",
            f"{AccountReverseNames.namespace}:{AccountReverseNames.ACCOUNT_ALREADY_ASSOCIATED}",
        ):
            with self.subTest(name=name):
                view = resolve(reverse(name)).func
                self.assertIs(view.view_class, ConsoleAppView)  # type: ignore[attr-defined]
        activate = django_reverse(
            f"{AccountReverseNames.namespace}:{AccountReverseNames.ACCOUNT_ACTIVATE}",
            kwargs={"uidb64": "MQ", "token": "a-token"},
        )
        self.assertEqual(activate, "/account/activate/MQ/a-token/")
        self.assertIs(resolve(activate).func.view_class, ConsoleAppView)  # type: ignore[attr-defined]

    def test_retired_urls_are_gone(self):
        """
        The duplicate and dead account urls answer 404, even for a staff user.

        ``/account/user/<id>/`` let staff edit any user's ``is_superuser`` flag.
        """
        self.client.force_login(self.admin_user)
        retired_paths = [
            "/account/login/",
            "/account/logout/",
            "/logout/",
            "/account/activation/",
            "/account/register/",
            "/account/api-keys/",
            "/account/users/",
            f"/account/user/{self.non_admin_user.pk}/",
            "/account/deactivate/",
            "/password-confirm/",
            "/dashboard/account/login/",
            "/dashboard/plugins/",
        ]
        for path in retired_paths:
            response = self.client.get(path)
            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, path)

        # a POST to the old user page must not change anyone
        response = self.client.post(
            f"/account/user/{self.non_admin_user.pk}/",
            data={"is_superuser": "on", "is_staff": "on"},
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.non_admin_user.refresh_from_db()
        self.assertFalse(self.non_admin_user.is_superuser)
