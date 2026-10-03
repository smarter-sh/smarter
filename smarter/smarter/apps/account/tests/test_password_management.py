"""
Test the password reset views, :mod:`smarter.apps.account.views.password_management`.

The password reset email is never sent: email_helper is patched.
"""

from http import HTTPStatus
from unittest.mock import patch
from urllib.parse import urlparse

from django.contrib.auth.models import User
from django.test import Client, RequestFactory
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.urls import AccountReverseNames
from smarter.apps.account.views.password_management import PasswordResetRequestView
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.token_generators import SmarterTokenExpiredError

MODULE = "smarter.apps.account.views.password_management"


class TestPasswordManagement(TestAccountMixin):
    """Test requesting a password reset, and resetting the password with the emailed link."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        patcher = patch(f"{MODULE}.email_helper")
        self.email_helper = patcher.start()
        self.addCleanup(patcher.stop)
        self.request_url = reverse(AccountReverseNames.ACCOUNT_PASSWORD_RESET_REQUEST)
        request = RequestFactory().get("/", HTTP_HOST="testserver")
        self.link_path = urlparse(
            PasswordResetRequestView().generate_password_reset_link(request, self.non_admin_user)
        ).path

    def test_request_form(self):
        self.assertEqual(self.client.get(self.request_url).status_code, HTTPStatus.OK)

    def test_request_reset(self):
        response = self.client.post(self.request_url, {"email": self.non_admin_user.email})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.email_helper.send_email.assert_called_once()
        self.assertEqual(self.email_helper.send_email.call_args.kwargs["to"], self.non_admin_user.email)

    def test_request_reset_unknown_and_invalid_email(self):
        self.assertEqual(self.client.post(self.request_url, {"email": "nobody@example.com"}).status_code, HTTPStatus.OK)
        self.assertEqual(
            self.client.post(self.request_url, {"email": "not an email"}).status_code, HTTPStatus.BAD_REQUEST
        )
        self.email_helper.send_email.assert_not_called()

    def test_generate_link_requires_a_user(self):
        with self.assertRaises(SmarterValueError):
            PasswordResetRequestView().generate_password_reset_link(None, "not a user")

    def test_reset_password(self):
        """Test that the link shows the new password form, and sets the new password."""
        self.assertEqual(self.client.get(self.link_path).status_code, HTTPStatus.OK)
        response = self.client.post(self.link_path, {"password": "new-Passw0rd!", "password_confirm": "new-Passw0rd!"})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertTrue(User.objects.get(pk=self.non_admin_user.pk).check_password("new-Passw0rd!"))

    def test_reset_password_errors(self):
        """Test mismatched and missing passwords, and invalid and expired links."""
        bad = {"password": "a", "password_confirm": "b"}
        self.assertEqual(self.client.post(self.link_path, bad).status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(self.client.post(self.link_path, {}).status_code, HTTPStatus.BAD_REQUEST)
        invalid = reverse(
            AccountReverseNames.PASSWORD_RESET_LINK, kwargs={"uidb64": "bm90LWEtdXNlcg", "token": "not-a-token"}
        )
        good = {"password": "x", "password_confirm": "x"}
        self.assertIn(self.client.get(invalid).status_code, (HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND))
        self.assertIn(self.client.post(invalid, good).status_code, (HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND))
        with patch(f"{MODULE}.PasswordResetView.expiring_token") as token:
            token.decode_link.side_effect = SmarterTokenExpiredError("expired")
            self.assertEqual(self.client.get(self.link_path).status_code, HTTPStatus.FORBIDDEN)
            self.assertEqual(self.client.post(self.link_path, good).status_code, HTTPStatus.FORBIDDEN)
            token.decode_link.side_effect = User.DoesNotExist()
            self.assertEqual(self.client.get(self.link_path).status_code, HTTPStatus.NOT_FOUND)
            self.assertEqual(self.client.post(self.link_path, good).status_code, HTTPStatus.NOT_FOUND)
        self.assertFalse(User.objects.get(pk=self.non_admin_user.pk).check_password("x"))
