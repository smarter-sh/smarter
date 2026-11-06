"""Tests of smarter.apps.account.sign_in: signing in with an email address, and signing up."""

from unittest import mock

from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import RequestFactory

from smarter.apps.account import sign_in
from smarter.apps.account.login_audit import LoginFailure
from smarter.apps.account.models import User
from smarter.apps.account.tests.mixins import TestAccountMixin

PASSWORD = "Correct-Horse-Battery-9"


class TestSignIn(TestAccountMixin):
    """Test sign_in_with_email(), email_is_taken(), awaits_activation() and sign_up()."""

    def setUp(self):
        super().setUp()
        self.email = f"sign_in_{self.hash_suffix}@example.com"
        self.user = User.objects.create_user(self.email, email=self.email, password=PASSWORD)
        self.addCleanup(User.objects.filter(email__iexact=self.email).delete)

    def request(self):
        request = RequestFactory().post("/api/web/account/login/")
        SessionMiddleware(lambda r: HttpResponse()).process_request(request)
        return request

    def test_sign_in(self):
        request = self.request()
        user = sign_in.sign_in_with_email(request, self.email, PASSWORD)
        self.assertEqual(user.pk, self.user.pk)  # type: ignore[union-attr]

    def test_failures_are_audited(self):
        """An unknown address and a wrong password both fail, each with its reason in the audit."""
        with mock.patch.object(sign_in, "log_login_failure") as log_login_failure:
            self.assertIsNone(sign_in.sign_in_with_email(self.request(), "nobody@example.com", PASSWORD))
            log_login_failure.assert_called_once_with("nobody@example.com", LoginFailure.UNKNOWN_ACCOUNT)
            log_login_failure.reset_mock()
            self.assertIsNone(sign_in.sign_in_with_email(self.request(), self.email, "wrong"))
            log_login_failure.assert_called_once()

    def test_email_is_taken_in_any_case(self):
        self.assertTrue(sign_in.email_is_taken(self.email.upper()))
        self.assertFalse(sign_in.email_is_taken("nobody@example.com"))

    def test_sign_up_creates_an_inactive_user_and_emails_the_link(self):
        """A new user can't sign in until they follow the emailed link."""
        email = f"sign_up_{self.hash_suffix}@example.com"
        self.addCleanup(User.objects.filter(email=email).delete)
        request = self.request()
        with mock.patch.object(sign_in, "send_activation_email") as send_activation_email:
            user = sign_in.sign_up(request, email, PASSWORD)
        self.assertEqual(user.username, email)
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password(PASSWORD))
        send_activation_email.assert_called_once_with(request, user)
        self.assertIsNone(sign_in.sign_in_with_email(self.request(), email, PASSWORD))

    def test_awaits_activation(self):
        """Only the right password of an inactive user who signed up with one says the account is waiting."""
        self.assertFalse(sign_in.awaits_activation(self.email, PASSWORD))
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertTrue(sign_in.awaits_activation(self.email.upper(), PASSWORD))
        self.assertFalse(sign_in.awaits_activation(self.email, "wrong"))
        self.assertFalse(sign_in.awaits_activation("nobody@example.com", PASSWORD))
