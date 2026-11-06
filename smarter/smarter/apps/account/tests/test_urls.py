# pylint: disable=wrong-import-position
"""Test the account app's urls, and that its retired urls are gone."""

from http import HTTPStatus

from django.test import Client
from waffle.testutils import override_switch

# our stuff
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.waffle import SmarterWaffleSwitches
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

    def test_root_account_urls(self):
        """Sign-in, sign-out, registration and password reset are served at the root."""
        self.verify_response("login_view", HTTPStatus.OK)
        self.verify_response("logout_view", HTTPStatus.FOUND)
        with override_switch(SmarterWaffleSwitches.ENABLE_ACCOUNT_REGISTRATION, active=True):
            self.verify_response(ConsoleReverseNames.register_view, HTTPStatus.OK)
        self.verify_response("account_password_reset_request", HTTPStatus.OK)

    def test_retired_urls_are_gone(self):
        """
        The duplicate and dead account urls answer 404, even for a staff user.

        ``/account/user/<id>/`` let staff edit any user's ``is_superuser`` flag.
        """
        self.client.force_login(self.admin_user)
        retired_paths = [
            "/account/login/",
            "/account/logout/",
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
