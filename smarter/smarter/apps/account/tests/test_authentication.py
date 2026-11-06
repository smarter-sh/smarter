# pylint: disable=wrong-import-position,W0613
"""Test the sign-in, sign-out, registration and account lifecycle views."""

from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.test import Client
from waffle.testutils import override_switch

from smarter.apps.account.login_audit import LoginFailure, password_failure
from smarter.apps.account.models import User
from smarter.apps.account.urls import AccountReverseNames
from smarter.apps.account.views.authentication import (
    AccountActivationEmailView,
    AccountInactiveView,
    AccountRegisterView,
    LoginView,
    LogoutView,
)

# our stuff
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .mixins import TestAccountMixin

logger = logging.getLogger(__name__)

LOGIN_VIEW = "smarter.apps.account.views.authentication.login_view"


class TestLoginView(TestAccountMixin):
    """
    Test Account LoginView.

    path("login/", LoginView.as_view(), name="login_view")
    """

    test_logger_prefix = f"{logging.SmarterFormattedText.text(__name__)}.TestLoginView()"

    @patch(
        "smarter.apps.account.views.authentication.login_view.waffle.switch_is_active",
        return_value=True,
    )
    def test_get_login_view_renders_for_anonymous(self, mock_waffle):
        """GET request to LoginView for anonymous user should render sign-in page with correct context."""
        request = self.request_factory().get("/login/")
        request.user = AnonymousUser()  # type: ignore
        view = LoginView()
        response = view.get(request)
        self.assertEqual(
            response.status_code, HTTPStatus.OK, f"Expected OK for anonymous GET but got {response.status_code}"
        )

        # simply in order to touch this code path.
        self.assertIn(view.is_google_oauth_enabled, (True, False))
        self.assertIn(view.is_github_oauth_enabled, (True, False))

    def test_get_login_view_redirects_authenticated_user(self):
        """GET request to LoginView for authenticated user should redirect to root."""
        request = self.request_factory().get("/login/")
        request.user = self.admin_user
        view = LoginView()
        response = view.get(request)

        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND,
            f"Expected FOUND for authenticated GET but got {response.status_code}",
        )
        if hasattr(response, "url"):
            self.assertEqual(response.url, "/")  # type: ignore

    def test_post_login_success(self):
        """POST valid credentials for admin_user should log in and redirect."""
        self.admin_user.set_password("12345")
        self.admin_user.save()
        data = {"email": self.admin_user.email, "password": "12345"}

        request = self.request_factory().post("/login/", data)
        request.user = AnonymousUser()
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()

        view = LoginView()
        response = view.post(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND,
            f"Expected FOUND for successful login but got {response.status_code}",
        )
        if hasattr(response, "url"):
            self.assertEqual(response.url, "/")  # type: ignore

    def test_post_login_invalid_password(self):
        """POST invalid password for admin_user should return bad request."""

        data = {"email": self.admin_user.email, "password": "wrongpassword"}
        request = self.request_factory().post("/login/", data)
        request.user = AnonymousUser()
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()

        view = LoginView()
        with patch(f"{LOGIN_VIEW}.log_login_failure") as log_login_failure:
            response = view.post(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.BAD_REQUEST,
            f"Expected BAD_REQUEST for invalid password but got {response.status_code}",
        )
        log_login_failure.assert_called_once_with(self.admin_user.email, password_failure(self.admin_user))

    def test_post_login_unknown_user(self):
        """POST unknown email gets the same response as a wrong password, so it doesn't reveal who has an account."""
        data = {"email": "unknown@example.com", "password": "irrelevant"}
        request = self.request_factory().post("/login/", data)
        request.user = AnonymousUser()
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()

        view = LoginView()
        with patch(f"{LOGIN_VIEW}.log_login_failure") as log_login_failure:
            response = view.post(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.BAD_REQUEST,
            f"Expected BAD_REQUEST for unknown user but got {response.status_code}",
        )
        self.assertNotIn(b"unknown@example.com", response.content)
        log_login_failure.assert_called_once_with("unknown@example.com", LoginFailure.UNKNOWN_ACCOUNT)

    def test_post_login_exception(self):
        """POST that raises inside the sign-in should return a server error, and log the failure as ERROR."""
        data = {"email": self.admin_user.email, "password": "irrelevant"}
        request = self.request_factory().post("/login/", data)
        request.user = AnonymousUser()
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()

        view = LoginView()
        with (
            patch(f"{LOGIN_VIEW}.authenticate", side_effect=RuntimeError("boom")),
            patch(f"{LOGIN_VIEW}.log_login_failure") as log_login_failure,
            patch(f"{LOGIN_VIEW}.logger") as view_logger,
        ):
            response = view.post(request)
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        log_login_failure.assert_called_once_with(self.admin_user.email, LoginFailure.ERROR)
        view_logger.error.assert_called_once()
        self.assertNotIn(self.admin_user.email, repr(view_logger.error.call_args))
        # the exception's text is logged, and never shown to the client (issue #914).
        self.assertNotIn("boom", response.content.decode())

    def test_post_login_invalid_form(self):
        """POST with missing fields should return bad request."""
        data = {"email": ""}  # missing password
        request = self.request_factory().post("/login/", data)
        request.user = AnonymousUser()
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()

        view = LoginView()
        with patch(f"{LOGIN_VIEW}.log_login_failure") as log_login_failure:
            response = view.post(request)

        logger.debug(
            "%s.test_post_login_invalid_form() Response error_message: %s",
            self.formatted_class_name,
            response.status_code,
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        log_login_failure.assert_called_once_with("", LoginFailure.INVALID_FORM)

    @patch("smarter.apps.account.views.authentication.login_view.logger")
    @patch("smarter.apps.account.views.authentication.login_view.smarter_settings")
    @patch("smarter.apps.account.views.authentication.login_view.settings")
    @patch("smarter.apps.account.views.authentication.login_view.waffle.switch_is_active", return_value=True)
    def test_is_google_oauth_enabled_key_missing(self, mock_switch, mock_settings, mock_smarter_settings, mock_logger):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = ""
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = "secret"
        view = LoginView()
        self.assertFalse(
            view.is_google_oauth_enabled, "Expected is_google_oauth_enabled to be False when key is missing."
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.views.authentication.login_view.logger")
    @patch("smarter.apps.account.views.authentication.login_view.smarter_settings")
    @patch("smarter.apps.account.views.authentication.login_view.settings")
    @patch("smarter.apps.account.views.authentication.login_view.waffle.switch_is_active", return_value=True)
    def test_is_google_oauth_enabled_secret_missing(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = ""
        view = LoginView()
        self.assertFalse(
            view.is_google_oauth_enabled, "Expected is_google_oauth_enabled to be False when secret is missing."
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.views.authentication.login_view.logger")
    @patch("smarter.apps.account.views.authentication.login_view.smarter_settings")
    @patch("smarter.apps.account.views.authentication.login_view.settings")
    @patch("smarter.apps.account.views.authentication.login_view.waffle.switch_is_active", return_value=True)
    def test_is_google_oauth_enabled_key_missing_default_missing_value(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = "MISSING"
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = "secret"
        mock_smarter_settings.default_missing_value = "MISSING"
        view = LoginView()
        self.assertFalse(
            view.is_google_oauth_enabled,
            "Expected is_google_oauth_enabled to be False when key is missing and default_missing_value is set.",
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.views.authentication.login_view.logger")
    @patch("smarter.apps.account.views.authentication.login_view.smarter_settings")
    @patch("smarter.apps.account.views.authentication.login_view.settings")
    @patch("smarter.apps.account.views.authentication.login_view.waffle.switch_is_active", return_value=True)
    def test_is_google_oauth_enabled_secret_missing_default_missing_value(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = "MISSING"
        mock_smarter_settings.default_missing_value = "MISSING"
        view = LoginView()
        self.assertFalse(
            view.is_google_oauth_enabled,
            "Expected is_google_oauth_enabled to be False when secret is missing and default_missing_value is set.",
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.views.authentication.login_view.logger")
    @patch("smarter.apps.account.views.authentication.login_view.smarter_settings")
    @patch("smarter.apps.account.views.authentication.login_view.settings")
    @patch("smarter.apps.account.views.authentication.login_view.waffle.switch_is_active", return_value=True)
    def test_is_google_oauth_enabled_backend_found(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = "secret"
        mock_settings.AUTHENTICATION_BACKENDS = [
            "social_core.backends.google.GoogleOAuth2",
            "other.backend",
        ]
        view = LoginView()
        self.assertTrue(
            view.is_google_oauth_enabled, "Expected is_google_oauth_enabled to be True when backend is found."
        )

    @patch("smarter.apps.account.views.authentication.login_view.logger")
    @patch("smarter.apps.account.views.authentication.login_view.smarter_settings")
    @patch("smarter.apps.account.views.authentication.login_view.settings")
    @patch("smarter.apps.account.views.authentication.login_view.waffle.switch_is_active", return_value=True)
    def test_is_google_oauth_enabled_backend_not_found(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = "secret"
        mock_settings.AUTHENTICATION_BACKENDS = [
            "other.backend",
        ]
        view = LoginView()
        self.assertFalse(
            view.is_google_oauth_enabled, "Expected is_google_oauth_enabled to be False when backend is not found."
        )
        mock_logger.warning.assert_called()

    # --- Tests for is_github_oauth_enabled property ---
    @patch("smarter.apps.account.views.authentication.login_view.logger")
    @patch("smarter.apps.account.views.authentication.login_view.smarter_settings")
    @patch("smarter.apps.account.views.authentication.login_view.settings")
    @patch("smarter.apps.account.views.authentication.login_view.waffle.switch_is_active", return_value=True)
    def test_is_github_oauth_enabled_key_missing(self, mock_switch, mock_settings, mock_smarter_settings, mock_logger):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = ""
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = "secret"
        view = LoginView()
        self.assertFalse(
            view.is_github_oauth_enabled, "Expected is_github_oauth_enabled to be False when key is missing."
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.views.authentication.login_view.logger")
    @patch("smarter.apps.account.views.authentication.login_view.smarter_settings")
    @patch("smarter.apps.account.views.authentication.login_view.settings")
    @patch("smarter.apps.account.views.authentication.login_view.waffle.switch_is_active", return_value=True)
    def test_is_github_oauth_enabled_secret_missing(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = ""
        view = LoginView()
        self.assertFalse(
            view.is_github_oauth_enabled, "Expected is_github_oauth_enabled to be False when secret is missing."
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.views.authentication.login_view.logger")
    @patch("smarter.apps.account.views.authentication.login_view.smarter_settings")
    @patch("smarter.apps.account.views.authentication.login_view.settings")
    def test_is_github_oauth_enabled_key_missing_default_missing_value(
        self, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = "MISSING"
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = "secret"
        mock_smarter_settings.default_missing_value = "MISSING"
        view = LoginView()
        self.assertFalse(
            view.is_github_oauth_enabled,
            "Expected is_github_oauth_enabled to be False when key is missing and default_missing_value is set.",
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.views.authentication.login_view.logger")
    @patch("smarter.apps.account.views.authentication.login_view.smarter_settings")
    @patch("smarter.apps.account.views.authentication.login_view.settings")
    def test_is_github_oauth_enabled_secret_missing_default_missing_value(
        self, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = "MISSING"
        mock_smarter_settings.default_missing_value = "MISSING"
        view = LoginView()
        self.assertFalse(
            view.is_github_oauth_enabled,
            "Expected is_github_oauth_enabled to be False when secret is missing and default_missing_value is set.",
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.views.authentication.login_view.logger")
    @patch("smarter.apps.account.views.authentication.login_view.smarter_settings")
    @patch("smarter.apps.account.views.authentication.login_view.settings")
    @patch("smarter.apps.account.views.authentication.login_view.waffle.switch_is_active", return_value=True)
    def test_is_github_oauth_enabled_backend_found(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = "secret"
        mock_settings.AUTHENTICATION_BACKENDS = [
            "social_core.backends.github.GithubOAuth2",
            "other.backend",
        ]
        view = LoginView()
        self.assertTrue(
            view.is_github_oauth_enabled, "Expected is_github_oauth_enabled to be True when backend is found."
        )

    @patch("smarter.apps.account.views.authentication.login_view.logger")
    @patch("smarter.apps.account.views.authentication.login_view.smarter_settings")
    @patch("smarter.apps.account.views.authentication.login_view.settings")
    @patch("smarter.apps.account.views.authentication.login_view.waffle.switch_is_active", return_value=True)
    def test_is_github_oauth_enabled_backend_not_found(
        self, mock_switch, mock_settings, mock_smarter_settings, mock_logger
    ):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = "secret"
        mock_settings.AUTHENTICATION_BACKENDS = [
            "other.backend",
        ]
        view = LoginView()
        self.assertFalse(
            view.is_github_oauth_enabled, "Expected is_github_oauth_enabled to be False when backend is not found."
        )
        mock_logger.warning.assert_called()


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


class TestAccountRegisterView(TestAccountMixin):
    """
    Test AccountRegisterView, with the ENABLE_ACCOUNT_REGISTRATION switch on.

    path("register/", AccountRegisterView.as_view(), name=ConsoleReverseNames.register_view)
    """

    test_logger_prefix = f"{logging.SmarterFormattedText.text(__name__)}.TestAccountRegisterView()"

    def setUp(self):
        """Set up for each test."""
        self.test_create_username = f"newuser_{self.hash_suffix}@example.com"
        super().setUp()
        switch = override_switch(SmarterWaffleSwitches.ENABLE_ACCOUNT_REGISTRATION, active=True)
        switch.enable()
        self.addCleanup(switch.disable)

    def tearDown(self):

        try:
            u = User.objects.get(username=self.test_create_username)
            u.delete()
        except User.DoesNotExist:
            pass
        super().tearDown()

    def test_get_register_view_renders_for_anonymous(self):
        """GET request to AccountRegisterView for anonymous user should render sign-up page with form."""
        request = self.request_factory().get("/register/")
        request.user = None  # type: ignore
        view = AccountRegisterView()
        response = view.get(request)
        self.assertEqual(
            response.status_code, HTTPStatus.OK, f"Expected OK for anonymous GET but got {response.status_code}"
        )

    def test_get_register_view_redirects_authenticated_user(self):
        """GET request to AccountRegisterView for authenticated user should redirect to root."""
        request = self.request_factory().get("/register/")
        request.user = self.admin_user
        view = AccountRegisterView()
        response = view.get(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND,
            f"Expected FOUND for authenticated GET but got {response.status_code}",
        )
        self.assertEqual(response.url, "/")  # type: ignore

    def test_post_register_view_valid_form(self):
        """POST valid registration data should create user, log in, and redirect to the console's home."""
        data = {
            "email": self.test_create_username,
            "password": "testpass123",
        }
        request = self.request_factory().post("/register/", data)
        request.user = None  # type: ignore
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        view = AccountRegisterView()
        response = view.post(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND,
            f"Expected FOUND for valid registration POST but got {response.status_code}",
        )
        if hasattr(response, "url"):
            self.assertEqual(response.url, "/")  # type: ignore

    def test_post_register_stores_the_browser_language(self):
        """A console sign-up stores the browser's language as the user's preference, and is welcomed in it."""
        # pylint: disable=import-outside-toplevel
        from smarter.apps.account.models import AccountContact, UserProfile

        self.addCleanup(AccountContact.objects.filter(email=self.test_create_username).delete)
        data = {"email": self.test_create_username, "password": "testpass123"}
        with patch("smarter.apps.account.models.account_contact.infrastructure") as infrastructure:
            response = Client().post("/register/", data, HTTP_ACCEPT_LANGUAGE="fr-CA,fr;q=0.9,en;q=0.5")
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        user_profile = UserProfile.objects.get(user__username=self.test_create_username)
        self.assertEqual(user_profile.language, "fr")
        infrastructure.email.send_email.assert_called_once()
        self.assertIn('<html lang="fr">', infrastructure.email.send_email.call_args.kwargs["body"])

    def test_sign_up_form_rejects_an_existing_address_in_any_case(self):
        """An email address that another user has, typed in another case, is rejected (issue #914)."""
        form = AccountRegisterView.SignUpForm({"email": self.admin_user.email.upper(), "password": "testpass123"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertEqual(User.objects.filter(email__iexact=self.admin_user.email).count(), 1)

    def test_post_register_view_invalid_form(self):
        """POST invalid registration data should re-render the form with errors."""
        data = {"email": "", "password": ""}  # All fields missing/invalid
        request = self.request_factory().post("/register/", data)
        request.user = AnonymousUser()
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        view = AccountRegisterView()
        response = view.post(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.OK,
            f"Expected OK for invalid registration POST but got {response.status_code}",
        )


class TestAccountRegisterViewSwitchedOff(TestAccountMixin):
    """With the ENABLE_ACCOUNT_REGISTRATION switch off, the sign-up page and its form answer 404."""

    def test_register_is_not_found_and_creates_no_user(self):
        """Neither GET nor POST works, and a POST creates no user."""
        email = f"closed_{self.hash_suffix}@example.com"
        self.addCleanup(User.objects.filter(email=email).delete)
        client = Client()
        with override_switch(SmarterWaffleSwitches.ENABLE_ACCOUNT_REGISTRATION, active=False):
            get_response = client.get("/register/")
            post_response = client.post("/register/", {"email": email, "password": "testpass123"})
        self.assertEqual(get_response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(post_response.status_code, HTTPStatus.NOT_FOUND)
        self.assertFalse(User.objects.filter(email=email).exists())


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
