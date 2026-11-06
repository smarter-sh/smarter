"""Tests of smarter.apps.account.password_reset: password reset links and their email."""

from http import HTTPStatus
from unittest import mock

from django.http import HttpResponse
from django.test import RequestFactory

from smarter.apps.account import email_links, password_reset
from smarter.apps.account.email_links import EmailLinkError
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.exceptions import SmarterValueError


class TestPasswordReset(TestAccountMixin):
    """Test making, emailing and reading back a password reset link."""

    def setUp(self):
        super().setUp()
        self.request = RequestFactory().get("/", HTTP_HOST="testserver")
        patcher = mock.patch.object(password_reset, "infrastructure")
        self.infrastructure = patcher.start()
        self.addCleanup(patcher.stop)

    def test_link_round_trip(self):
        """A link's parts give back its user."""
        link = password_reset.password_reset_link(self.request, self.non_admin_user)
        self.assertIn("/password-reset-link/", link)
        _, uidb64, token, _ = link.rsplit("/", 3)
        self.assertEqual(password_reset.user_from_reset_link(uidb64, token).pk, self.non_admin_user.pk)

    def test_link_needs_a_user(self):
        with self.assertRaises(SmarterValueError):
            password_reset.password_reset_link(self.request, "not a user")  # type: ignore[arg-type]

    def test_bad_link(self):
        with self.assertRaises(EmailLinkError) as raised:
            password_reset.user_from_reset_link("bm90LWEtdXNlcg", "not-a-token")
        self.assertIn(raised.exception.status, (HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND))

    def test_email(self):
        """A known address gets an email, without a blind copy to the admin; an unknown one gets none."""
        self.assertTrue(password_reset.send_password_reset_email(self.request, self.non_admin_user.email))
        kwargs = self.infrastructure.email.send_email.call_args.kwargs
        self.assertEqual(kwargs["to"], self.non_admin_user.email)
        self.assertFalse(kwargs["bcc_admin"])
        self.assertFalse(password_reset.send_password_reset_email(self.request, "nobody@example.com"))
        self.infrastructure.email.send_email.assert_called_once()

    def test_email_that_cannot_render(self):
        """A template that fails to render raises, and sends nothing."""
        failed = HttpResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR)
        with mock.patch.object(email_links.SmarterView, "render_clean_html", return_value=failed):
            with self.assertRaises(RuntimeError):
                password_reset.send_password_reset_email(self.request, self.non_admin_user.email)
        self.infrastructure.email.send_email.assert_not_called()
