"""Tests of smarter.apps.account.activation: activation links, their email, and activating an account."""

from http import HTTPStatus
from unittest import mock

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory

from smarter.apps.account import activation, email_links
from smarter.apps.account.email_links import EmailLinkError
from smarter.apps.account.models import User
from smarter.apps.account.tests.mixins import TestAccountMixin

PASSWORD = "Correct-Horse-Battery-9"


class TestActivation(TestAccountMixin):
    """Test emailing an activation link, and activating an account with it."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(activation, "infrastructure")
        self.infrastructure = patcher.start()
        self.addCleanup(patcher.stop)
        self.email = f"activation_{self.hash_suffix}@example.com"
        self.user = User.objects.create_user(self.email, email=self.email, password=PASSWORD, is_active=False)
        self.addCleanup(User.objects.filter(pk=self.user.pk).delete)

    def request(self):
        """A request with a session, which activate() signs the user in to."""
        request = RequestFactory().post("/", HTTP_HOST="testserver")
        SessionMiddleware(lambda r: HttpResponse()).process_request(request)
        return request

    def link_parts(self) -> tuple[str, str]:
        """The uidb64 and token of a new activation link for the user."""
        link = activation.activation_link(self.request(), self.user)
        self.assertIn("/account/activate/", link)
        _, uidb64, token, _ = link.rsplit("/", 3)
        return uidb64, token

    def test_can_activate_by_email(self):
        """Only an inactive user who signed up with a password; a social sign-in's user waits for an admin."""
        self.assertTrue(activation.can_activate_by_email(self.user))
        self.assertFalse(activation.can_activate_by_email(self.non_admin_user))
        social_user = User(username="social", email="social@example.com", is_active=False)
        social_user.set_unusable_password()
        self.assertFalse(activation.can_activate_by_email(social_user))

    def test_email(self):
        """The email goes to the user, with the link, and without a blind copy to the admin."""
        activation.send_activation_email(self.request(), self.user)
        kwargs = self.infrastructure.email.send_email.call_args.kwargs
        self.assertEqual(kwargs["to"], self.email)
        self.assertFalse(kwargs["bcc_admin"])
        self.assertIn("/account/activate/", kwargs["body"])

    def test_resend(self):
        """A new link goes only to an inactive user who may activate by email."""
        self.assertTrue(activation.resend_activation_email(self.request(), self.email.upper()))
        self.assertFalse(activation.resend_activation_email(self.request(), "nobody@example.com"))
        self.assertFalse(activation.resend_activation_email(self.request(), self.non_admin_user.email))
        self.infrastructure.email.send_email.assert_called_once()

    def test_email_that_cannot_render(self):
        """A template that fails to render raises, and sends nothing."""
        failed = HttpResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR)
        with mock.patch.object(email_links.SmarterView, "render_clean_html", return_value=failed):
            with self.assertRaises(RuntimeError):
                activation.send_activation_email(self.request(), self.user)
        self.infrastructure.email.send_email.assert_not_called()

    def test_activate(self):
        """The link activates the user and signs them in, once."""
        uidb64, token = self.link_parts()
        request = self.request()
        user = activation.activate(request, uidb64, token)
        self.assertEqual(user.pk, self.user.pk)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertEqual(request.session["_auth_user_id"], str(self.user.pk))
        # signing in changed the user's last sign-in, which the token hashes.
        with self.assertRaises(EmailLinkError) as raised:
            activation.activate(self.request(), uidb64, token)
        self.assertEqual(raised.exception.status, HTTPStatus.BAD_REQUEST)

    def test_bad_link(self):
        with self.assertRaises(EmailLinkError):
            activation.activate(self.request(), "bm90LWEtdXNlcg", "not-a-token")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
