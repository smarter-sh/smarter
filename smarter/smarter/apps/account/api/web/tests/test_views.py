"""Tests of smarter.apps.account.api.web.views: the console's account api, /api/web/account/."""

import itertools
from http import HTTPStatus
from unittest import mock
from urllib.parse import urlparse

from django.test import Client, RequestFactory
from waffle.testutils import override_switch

from smarter.apps.account.activation import activation_link
from smarter.apps.account.api.web import views
from smarter.apps.account.api.web.contract import AccountErrors, AccountMessage
from smarter.apps.account.api.web.urls import AccountApiWebReverseNames
from smarter.apps.account.models import User
from smarter.apps.account.password_reset import password_reset_link
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.web.session.contract import ConsoleSession
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.token_generators import SmarterTokenExpiredError
from smarter.lib.django.waffle import SmarterWaffleSwitches

PASSWORD = "Correct-Horse-Battery-9"
"""A password that Django's validators accept."""

RESET_MODULE = "smarter.apps.account.password_reset"
ACTIVATION_MODULE = "smarter.apps.account.activation"
LINKS_MODULE = "smarter.apps.account.email_links"
CSRF_MODULE = "smarter.lib.django.middleware.csrf"

# each test signs in from its own address, so that the credentials rate limit, which is counted per
# address, never carries over from another test.
client_addresses = (f"10.9.{i // 250}.{i % 250 + 1}" for i in itertools.count())


def account_url(name: str, **kwargs) -> str:
    """The path of an account api endpoint."""
    if kwargs:
        # smarter.lib.django.shortcuts.reverse() doesn't take kwargs: see smarter-python-testing.
        # pylint: disable=import-outside-toplevel
        from django.urls import reverse as django_reverse

        return django_reverse(f"{AccountApiWebReverseNames.namespace}:{name}", kwargs=kwargs)
    return reverse(AccountApiWebReverseNames.namespace, name)


class AccountApiTestBase(TestAccountMixin):
    """A user with a known password, and a client with its own address."""

    def setUp(self):
        super().setUp()
        self.client = Client(REMOTE_ADDR=next(client_addresses))
        self.email = f"account_api_{self.hash_suffix}@example.com"
        self.user = User.objects.create_user(self.email, email=self.email, password=PASSWORD)
        self.addCleanup(User.objects.filter(pk=self.user.pk).delete)

    def tearDown(self):
        self.client.logout()
        super().tearDown()

    def post(self, name: str, body: dict, **kwargs):
        """POST a JSON body to an account api endpoint."""
        return self.client.post(account_url(name, **kwargs), body, content_type="application/json")

    def errors(self, response) -> AccountErrors:
        """The response, as AccountErrors."""
        return AccountErrors.model_validate(response.json())


class TestSignIn(AccountApiTestBase):
    """POST /api/web/account/login/ and logout/."""

    def test_urls(self):
        self.assertEqual(account_url(AccountApiWebReverseNames.sign_in), "/api/web/account/login/")
        self.assertEqual(account_url(AccountApiWebReverseNames.sign_out), "/api/web/account/logout/")

    def test_sign_in_and_out(self):
        """Signing in answers with the user's session, and signing out with a visitor's."""
        response = self.post(AccountApiWebReverseNames.sign_in, {"email": self.email, "password": PASSWORD})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        session = ConsoleSession.model_validate(response.json())
        self.assertTrue(session.is_authenticated)
        self.assertEqual(session.user.email, self.email)  # type: ignore[union-attr]

        response = self.post(AccountApiWebReverseNames.sign_out, {})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(ConsoleSession.model_validate(response.json()).is_authenticated)

    def test_wrong_password_and_unknown_address_answer_alike(self):
        """An unknown address and a wrong password get the same 400, which names neither."""
        wrong_password = self.post(AccountApiWebReverseNames.sign_in, {"email": self.email, "password": "nope"})
        unknown = self.post(AccountApiWebReverseNames.sign_in, {"email": "nobody@example.com", "password": PASSWORD})
        self.assertEqual(wrong_password.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(unknown.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(wrong_password.json(), unknown.json())
        self.assertNotIn("nobody@example.com", unknown.content.decode())

    def test_invalid_body(self):
        """A body without the fields, or that isn't JSON, is refused."""
        response = self.post(AccountApiWebReverseNames.sign_in, {"email": self.email})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(self.errors(response).detail, "The request is invalid.")
        response = self.client.post(
            account_url(AccountApiWebReverseNames.sign_in), "not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_needs_the_csrf_token(self):
        """
        On a deployed platform, a POST without the CSRF token is refused, and one with it is accepted.

        The local environment skips the check (see SmarterCsrfViewMiddleware.process_view), so the test
        runs the middleware with a copy of the settings whose environment is prod.
        """
        deployed = smarter_settings.model_copy(update={"environment": SmarterEnvironments.PROD})
        client = Client(enforce_csrf_checks=True, REMOTE_ADDR=next(client_addresses))
        url = account_url(AccountApiWebReverseNames.sign_in)
        body = {"email": self.email, "password": PASSWORD}
        with mock.patch(f"{CSRF_MODULE}.smarter_settings", deployed):
            refused = client.post(url, body, content_type="application/json")
            token = "a" * 32
            client.cookies["csrftoken"] = token
            accepted = client.post(url, body, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(refused.status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(accepted.status_code, HTTPStatus.OK)

    def test_only_post(self):
        response = self.client.get(account_url(AccountApiWebReverseNames.sign_in))
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_inactive_account(self):
        """The right password of an account that isn't activated yet gets 403; a wrong one, the usual 400."""
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        response = self.post(AccountApiWebReverseNames.sign_in, {"email": self.email, "password": PASSWORD})
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertIn("isn't activated yet", self.errors(response).detail)
        response = self.post(AccountApiWebReverseNames.sign_in, {"email": self.email, "password": "nope"})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_rate_limit(self):
        """Too many attempts from one address are refused with 429 and Retry-After."""
        with mock.patch.object(views, "credentials_throttle_wait", return_value=42):
            response = self.post(AccountApiWebReverseNames.sign_in, {"email": self.email, "password": PASSWORD})
        self.assertEqual(response.status_code, HTTPStatus.TOO_MANY_REQUESTS)
        self.assertEqual(response["Retry-After"], "42")


class TestSignUp(AccountApiTestBase):
    """POST /api/web/account/register/."""

    def setUp(self):
        super().setUp()
        self.new_email = f"new_{self.hash_suffix}@example.com"
        self.addCleanup(User.objects.filter(email=self.new_email).delete)
        switch = override_switch(SmarterWaffleSwitches.ENABLE_ACCOUNT_REGISTRATION, active=True)
        switch.enable()
        self.addCleanup(switch.disable)
        patcher = mock.patch(f"{ACTIVATION_MODULE}.infrastructure")
        self.infrastructure = patcher.start()
        self.addCleanup(patcher.stop)

    def sign_up(self, email: str, password: str = PASSWORD):
        return self.post(AccountApiWebReverseNames.sign_up, {"email": email, "password": password})

    def test_sign_up(self):
        """A new user is created inactive, isn't signed in, and is emailed an activation link."""
        response = self.sign_up(self.new_email)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        AccountMessage.model_validate(response.json())
        user = User.objects.get(email=self.new_email)
        self.assertFalse(user.is_active)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.infrastructure.email.send_email.call_args.kwargs["to"], self.new_email)

    def test_email_that_cannot_render(self):
        """The user is created, and can ask for a new link; the response is a 500."""
        with mock.patch.object(views, "sign_up", side_effect=RuntimeError("template")):
            response = self.sign_up(self.new_email)
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_switched_off(self):
        """While registration is off, the endpoint is not found, and creates nobody."""
        with override_switch(SmarterWaffleSwitches.ENABLE_ACCOUNT_REGISTRATION, active=False):
            response = self.sign_up(self.new_email)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertFalse(User.objects.filter(email=self.new_email).exists())

    def test_field_errors(self):
        """An invalid or taken address, and a weak password, are each reported on their field."""
        response = self.sign_up("not-an-email", "123")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        errors = self.errors(response)
        self.assertEqual(set(errors.field_errors), {"email", "password"})

        response = self.sign_up(self.email.upper())
        errors = self.errors(response)
        self.assertEqual(
            errors.field_errors["email"], ["An account with this email address already exists. Please sign in."]
        )

    def test_password_like_the_address_is_refused(self):
        """Django's similarity validator compares the password with the would-be user's address."""
        response = self.sign_up(self.new_email, self.new_email)
        self.assertIn("password", self.errors(response).field_errors)
        self.assertFalse(User.objects.filter(email=self.new_email).exists())

    def test_invalid_body(self):
        response = self.post(AccountApiWebReverseNames.sign_up, {"email": self.new_email})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_rate_limit(self):
        with mock.patch.object(views, "credentials_throttle_wait", return_value=5):
            response = self.sign_up(self.new_email)
        self.assertEqual(response.status_code, HTTPStatus.TOO_MANY_REQUESTS)


class TestPasswordReset(AccountApiTestBase):
    """POST /api/web/account/password-reset-request/, and /api/web/account/password-reset/<uidb64>/<token>/."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch(f"{RESET_MODULE}.infrastructure")
        self.infrastructure = patcher.start()
        self.addCleanup(patcher.stop)
        request = RequestFactory().get("/", HTTP_HOST="testserver")
        link_path = urlparse(password_reset_link(request, self.user)).path
        # /password-reset-link/<uidb64>/<token>/
        _, _, self.uidb64, self.token, _ = link_path.split("/")

    def request_reset(self, email: str):
        return self.post(AccountApiWebReverseNames.password_reset_request, {"email": email})

    def reset(self, body: dict, uidb64: str = "", token: str = ""):
        return self.post(
            AccountApiWebReverseNames.password_reset,
            body,
            uidb64=uidb64 or self.uidb64,
            token=token or self.token,
        )

    def test_request_answers_alike(self):
        """A known and an unknown address get the same answer, and only the known one gets an email."""
        known = self.request_reset(self.email)
        unknown = self.request_reset("nobody@example.com")
        self.assertEqual(known.status_code, HTTPStatus.OK)
        self.assertEqual(known.json(), unknown.json())
        AccountMessage.model_validate(known.json())
        self.infrastructure.email.send_email.assert_called_once()
        self.assertEqual(self.infrastructure.email.send_email.call_args.kwargs["to"], self.email)

    def test_request_errors(self):
        """An invalid address is refused on its field; an email that can't be rendered is a 500."""
        response = self.request_reset("not-an-email")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("email", self.errors(response).field_errors)
        response = self.post(AccountApiWebReverseNames.password_reset_request, {})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        with mock.patch.object(views, "send_password_reset_email", side_effect=RuntimeError("template")):
            response = self.request_reset(self.email)
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_request_rate_limit(self):
        with mock.patch.object(views, "credentials_throttle_wait", return_value=5):
            response = self.request_reset(self.email)
        self.assertEqual(response.status_code, HTTPStatus.TOO_MANY_REQUESTS)

    def test_check_link(self):
        """GET answers whether the link can be used."""
        url = account_url(AccountApiWebReverseNames.password_reset, uidb64=self.uidb64, token=self.token)
        self.assertEqual(self.client.get(url).status_code, HTTPStatus.OK)
        bad = account_url(AccountApiWebReverseNames.password_reset, uidb64=self.uidb64, token="not-a-token")
        self.assertEqual(self.client.get(bad).status_code, HTTPStatus.BAD_REQUEST)
        with mock.patch(f"{LINKS_MODULE}.expiring_token") as token:
            token.decode_link.side_effect = SmarterTokenExpiredError("expired")
            self.assertEqual(self.client.get(url).status_code, HTTPStatus.FORBIDDEN)
            token.decode_link.side_effect = User.DoesNotExist()
            self.assertEqual(self.client.get(url).status_code, HTTPStatus.NOT_FOUND)

    def test_reset(self):
        """A valid link and an acceptable password set the new password."""
        new_password = "Another-Strong-Passw0rd"
        response = self.reset({"password": new_password, "passwordConfirm": new_password})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_reset_errors(self):
        """Mismatched or weak passwords, a bad body, and a bad link change nothing."""
        response = self.reset({"password": "Another-Strong-Passw0rd", "passwordConfirm": "different"})
        self.assertIn("passwordConfirm", self.errors(response).field_errors)
        response = self.reset({"password": "123", "passwordConfirm": "123"})
        self.assertIn("password", self.errors(response).field_errors)
        response = self.reset({"password": "x"})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response = self.reset({"password": "x", "passwordConfirm": "x"}, token="not-a-token")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))


class TestActivation(AccountApiTestBase):
    """POST /api/web/account/activate/<uidb64>/<token>/ and activation-resend/."""

    def setUp(self):
        super().setUp()
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.user.refresh_from_db()
        patcher = mock.patch(f"{ACTIVATION_MODULE}.infrastructure")
        self.infrastructure = patcher.start()
        self.addCleanup(patcher.stop)
        request = RequestFactory().get("/", HTTP_HOST="testserver")
        link_path = urlparse(activation_link(request, self.user)).path
        # /account/activate/<uidb64>/<token>/
        _, _, _, self.uidb64, self.token, _ = link_path.split("/")

    def activate(self, token: str = ""):
        return self.post(AccountApiWebReverseNames.activate, {}, uidb64=self.uidb64, token=token or self.token)

    def resend(self, email: str):
        return self.post(AccountApiWebReverseNames.activation_resend, {"email": email})

    def test_urls(self):
        self.assertEqual(
            account_url(AccountApiWebReverseNames.activate, uidb64="MQ", token="t"), "/api/web/account/activate/MQ/t/"
        )
        self.assertEqual(
            account_url(AccountApiWebReverseNames.activation_resend), "/api/web/account/activation-resend/"
        )

    def test_activate(self):
        """The link activates the user, and answers with their session; it can't be used again."""
        response = self.activate()
        self.assertEqual(response.status_code, HTTPStatus.OK)
        session = ConsoleSession.model_validate(response.json())
        self.assertTrue(session.is_authenticated)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.client.logout()
        self.assertEqual(self.activate().status_code, HTTPStatus.BAD_REQUEST)

    def test_bad_link(self):
        response = self.activate(token="not-a-token")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            self.client.get(account_url(AccountApiWebReverseNames.activate, uidb64="MQ", token="t")).status_code,
            HTTPStatus.METHOD_NOT_ALLOWED,
        )
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_resend_answers_alike(self):
        """A waiting account, an active one and an unknown address get the same answer; only the first an email."""
        waiting = self.resend(self.email)
        active = self.resend(self.non_admin_user.email)
        unknown = self.resend("nobody@example.com")
        self.assertEqual(waiting.status_code, HTTPStatus.OK)
        self.assertEqual(waiting.json(), active.json())
        self.assertEqual(waiting.json(), unknown.json())
        AccountMessage.model_validate(waiting.json())
        self.infrastructure.email.send_email.assert_called_once()
        self.assertEqual(self.infrastructure.email.send_email.call_args.kwargs["to"], self.email)

    def test_resend_errors(self):
        """An invalid address or body is refused; an email that can't be rendered is a 500; and it is rate limited."""
        response = self.resend("not-an-email")
        self.assertIn("email", self.errors(response).field_errors)
        response = self.post(AccountApiWebReverseNames.activation_resend, {})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        with mock.patch.object(views, "resend_activation_email", side_effect=RuntimeError("template")):
            response = self.resend(self.email)
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        with mock.patch.object(views, "credentials_throttle_wait", return_value=5):
            response = self.resend(self.email)
        self.assertEqual(response.status_code, HTTPStatus.TOO_MANY_REQUESTS)
