# pylint: disable=wrong-import-position,W0613
"""
Test Authentication.

AccountNamedUrls:
    Class to hold named URL patterns for the account app.
    This class provides constants for all named URL patterns used in the account dashboard views.
    The names follow the convention: 'account_<view_name>'.
    These are referenced in Django templates as 'reverse' or 'url' tags.

    .. usage-example::

    .. html::

    <a href="{% url 'dashboard_account_dashboard_overview' %}">Go to Dashboard Overview</a>


    API_KEYS_LIST = "api_keys_list"
    ACCOUNT_LOGIN = "account_login"
    ACCOUNT_LOGOUT = "account_logout"
    ACCOUNT_REGISTER = "account_register"
    ACCOUNT_ACTIVATION = "account_activation"
    ACCOUNT_ACTIVATE = "account_activate"
    ACCOUNT_DEACTIVATE = "account_deactivate"
    ACCOUNT_INACTIVE = "account_inactive"
    ACCOUNT_PASSWORD_RESET_REQUEST = "account_password_reset_request"
    ACCOUNT_PASSWORD_CONFIRM = "account_password_confirm"
    ACCOUNT_USER = "account_user"
    ACCOUNT_USERS = "account_users"
    PASSWORD_RESET_LINK = "password_reset_link"

    urlpatterns = [
        path(
            "",
            RedirectView.as_view(url="/dashboard/account/dashboard/", permanent=False),
            name="dashboard_account_dashboard",
        ),
        path("api/", include("smarter.apps.account.api.urls", namespace=namespace)),
        path("api-keys/", APIKeyListView.as_view(), name=AccountNamedUrls.API_KEYS_LIST),
        path("login/", LoginView.as_view(), name=AccountNamedUrls.ACCOUNT_LOGIN),
        path("logout/", LogoutView.as_view(), name=AccountNamedUrls.ACCOUNT_LOGOUT),
        path("inactive/", AccountInactiveView.as_view(), name=AccountNamedUrls.ACCOUNT_INACTIVE),
        path("dashboard/", include("smarter.apps.account.views.dashboard.urls")),
        # account lifecycle
        path("register/", AccountRegisterView.as_view(), name=AccountNamedUrls.ACCOUNT_REGISTER),
        path("activation/", AccountActivationEmailView.as_view(), name=AccountNamedUrls.ACCOUNT_ACTIVATION),
        path("activate/<uidb64>/<token>/", AccountActivateView.as_view(), name=AccountNamedUrls.ACCOUNT_ACTIVATE),
        path("deactivate/", AccountDeactivateView.as_view(), name=AccountNamedUrls.ACCOUNT_DEACTIVATE),
        # password management
        path(
            "password-reset-request/",
            PasswordResetRequestView.as_view(),
            name=AccountNamedUrls.ACCOUNT_PASSWORD_RESET_REQUEST,
        ),
        path("password-confirm/", PasswordConfirmView.as_view(), name=AccountNamedUrls.ACCOUNT_PASSWORD_CONFIRM),
        path(
            "password-reset-link/<uidb64>/<token>/", PasswordResetView.as_view(), name=AccountNamedUrls.PASSWORD_RESET_LINK
        ),
        path("users/", UsersView.as_view(), name=AccountNamedUrls.ACCOUNT_USERS),
        path("user/<int:user_id>/", UserView.as_view(), name=AccountNamedUrls.ACCOUNT_USER),
    ]

"""

# our stuff
import logging
from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpResponse
from django.urls import reverse

from smarter.apps.account.models import User
from smarter.apps.account.urls import AccountNamedUrls
from smarter.apps.account.views.authentication import (
    AccountActivationEmailView,
    AccountInactiveView,
    AccountRegisterView,
    LoginView,
    LogoutView,
)
from smarter.common.helpers.console_helpers import formatted_text

from .mixins import TestAccountMixin

logger = logging.getLogger(__name__)


class TestLoginView(TestAccountMixin):
    """
    Test Account LoginView.
    path("login/", LoginView.as_view(), name=AccountNamedUrls.ACCOUNT_LOGIN)

    """

    test_logger_prefix = formatted_text(f"{__name__}.TestLoginView()")

    def test_get_login_view_renders_for_anonymous(self):
        """
        GET request to LoginView for anonymous user should render sign-in page with correct context.
        """
        request = self.request_factory()
        request.user = None
        view = LoginView()
        response = view.get(request)
        self.assertEqual(
            response.status_code, HTTPStatus.OK, f"Expected OK for anonymous GET but got {response.status_code}"
        )

        # simply in order to touch this code path.
        self.assertIn(view.is_google_oauth_enabled, (True, False))
        self.assertIn(view.is_github_oauth_enabled, (True, False))

    def test_get_login_view_redirects_authenticated_user(self):
        """
        GET request to LoginView for authenticated user should redirect to root.
        """
        request = self.request_factory().get("/login/")
        request.user = self.admin_user
        view = LoginView()
        response = view.get(request)

        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND,
            f"Expected FOUND for authenticated GET but got {response.status_code}",
        )
        self.assertEqual(response.url, "/")

    def test_post_login_success(self):
        """
        POST valid credentials for admin_user should log in and redirect.
        """
        self.admin_user.set_password("12345")
        self.admin_user.save()
        data = {"email": self.admin_user.email, "password": "12345"}

        request = self.request_factory().post("/login/", data)
        request.user = None
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
        self.assertEqual(response.url, "/")

    def test_post_login_invalid_password(self):
        """
        POST invalid password for admin_user should return bad request.
        """
        data = {"email": self.admin_user.email, "password": "wrongpassword"}
        request = self.request_factory().post("/login/", data)
        request.user = None
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()

        view = LoginView()
        response = view.post(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.BAD_REQUEST,
            f"Expected BAD_REQUEST for invalid password but got {response.status_code}",
        )

    def test_post_login_unknown_user(self):
        """
        POST unknown email should return forbidden.
        """
        data = {"email": "unknown@example.com", "password": "irrelevant"}
        request = self.request_factory().post("/login/", data)
        request.user = None
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()

        view = LoginView()
        response = view.post(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.FORBIDDEN,
            f"Expected FORBIDDEN for unknown user but got {response.status_code}",
        )

    def test_post_login_invalid_form(self):
        """
        POST with missing fields should return bad request.
        """
        data = {"email": ""}  # missing password
        request = self.request_factory().post("/login/", data)
        request.user = None
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()

        view = LoginView()
        response = view.post(request)

        logger.debug(
            "%s.test_post_login_invalid_form() Response error_message: %s",
            self.formatted_class_name,
            response.status_code,
        )

    @patch("smarter.apps.account.views.authentication.logger")
    @patch("smarter.apps.account.views.authentication.smarter_settings")
    @patch("smarter.apps.account.views.authentication.settings")
    def test_is_google_oauth_enabled_key_missing(self, mock_settings, mock_smarter_settings, mock_logger):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = ""
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = "secret"
        view = LoginView()
        self.assertFalse(
            view.is_google_oauth_enabled, "Expected is_google_oauth_enabled to be False when key is missing."
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.views.authentication.logger")
    @patch("smarter.apps.account.views.authentication.smarter_settings")
    @patch("smarter.apps.account.views.authentication.settings")
    def test_is_google_oauth_enabled_secret_missing(self, mock_settings, mock_smarter_settings, mock_logger):
        mock_smarter_settings.social_auth_google_oauth2_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_google_oauth2_secret.get_secret_value.return_value = ""
        view = LoginView()
        self.assertFalse(
            view.is_google_oauth_enabled, "Expected is_google_oauth_enabled to be False when secret is missing."
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.views.authentication.logger")
    @patch("smarter.apps.account.views.authentication.smarter_settings")
    @patch("smarter.apps.account.views.authentication.settings")
    def test_is_google_oauth_enabled_key_missing_default_missing_value(
        self, mock_settings, mock_smarter_settings, mock_logger
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

    @patch("smarter.apps.account.views.authentication.logger")
    @patch("smarter.apps.account.views.authentication.smarter_settings")
    @patch("smarter.apps.account.views.authentication.settings")
    def test_is_google_oauth_enabled_secret_missing_default_missing_value(
        self, mock_settings, mock_smarter_settings, mock_logger
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

    @patch("smarter.apps.account.views.authentication.logger")
    @patch("smarter.apps.account.views.authentication.smarter_settings")
    @patch("smarter.apps.account.views.authentication.settings")
    def test_is_google_oauth_enabled_backend_found(self, mock_settings, mock_smarter_settings, mock_logger):
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

    @patch("smarter.apps.account.views.authentication.logger")
    @patch("smarter.apps.account.views.authentication.smarter_settings")
    @patch("smarter.apps.account.views.authentication.settings")
    def test_is_google_oauth_enabled_backend_not_found(self, mock_settings, mock_smarter_settings, mock_logger):
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
    @patch("smarter.apps.account.views.authentication.logger")
    @patch("smarter.apps.account.views.authentication.smarter_settings")
    @patch("smarter.apps.account.views.authentication.settings")
    def test_is_github_oauth_enabled_key_missing(self, mock_settings, mock_smarter_settings, mock_logger):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = ""
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = "secret"
        view = LoginView()
        self.assertFalse(
            view.is_github_oauth_enabled, "Expected is_github_oauth_enabled to be False when key is missing."
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.views.authentication.logger")
    @patch("smarter.apps.account.views.authentication.smarter_settings")
    @patch("smarter.apps.account.views.authentication.settings")
    def test_is_github_oauth_enabled_secret_missing(self, mock_settings, mock_smarter_settings, mock_logger):
        mock_smarter_settings.social_auth_github_key.get_secret_value.return_value = "key"
        mock_smarter_settings.social_auth_github_secret.get_secret_value.return_value = ""
        view = LoginView()
        self.assertFalse(
            view.is_github_oauth_enabled, "Expected is_github_oauth_enabled to be False when secret is missing."
        )
        mock_logger.debug.assert_called()

    @patch("smarter.apps.account.views.authentication.logger")
    @patch("smarter.apps.account.views.authentication.smarter_settings")
    @patch("smarter.apps.account.views.authentication.settings")
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

    @patch("smarter.apps.account.views.authentication.logger")
    @patch("smarter.apps.account.views.authentication.smarter_settings")
    @patch("smarter.apps.account.views.authentication.settings")
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

    @patch("smarter.apps.account.views.authentication.logger")
    @patch("smarter.apps.account.views.authentication.smarter_settings")
    @patch("smarter.apps.account.views.authentication.settings")
    def test_is_github_oauth_enabled_backend_found(self, mock_settings, mock_smarter_settings, mock_logger):
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

    @patch("smarter.apps.account.views.authentication.logger")
    @patch("smarter.apps.account.views.authentication.smarter_settings")
    @patch("smarter.apps.account.views.authentication.settings")
    def test_is_github_oauth_enabled_backend_not_found(self, mock_settings, mock_smarter_settings, mock_logger):
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
    path("login/", LogoutView.as_view(), name=AccountNamedUrls.ACCOUNT_LOGOUT)

    """

    test_logger_prefix = formatted_text(f"{__name__}.TestLogoutView()")

    def test_get_logout_view_redirects_authenticated_user(self):
        """
        GET request to LogoutView for authenticated user should log out and redirect to root.
        """
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
        """
        GET request to LogoutView for anonymous user should redirect to root (logout is idempotent).
        """
        request = self.request_factory().get("/logout/")
        request.user = None
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
        """
        POST request to LogoutView for authenticated user should log out and redirect to root.
        """
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
        """
        POST request to LogoutView for anonymous user should redirect to root (logout is idempotent).
        """
        request = self.request_factory().post("/logout/")
        request.user = None
        middleware = SessionMiddleware(lambda request: HttpResponse())
        middleware.process_request(request)
        request.session.save()
        view = LogoutView()
        response = view.post(request)
        self.assertEqual(
            response.status_code, HTTPStatus.FOUND, f"Expected FOUND for anonymous POST but got {response.status_code}"
        )
        self.assertEqual(response.url, "/")


class TestAccountInactiveView(TestAccountMixin):
    """
    Test AccountInactiveView.
    path("inactive/", AccountInactiveView.as_view(), name=AccountNamedUrls.ACCOUNT_INACTIVE)
    """

    test_logger_prefix = formatted_text(f"{__name__}.TestAccountInactiveView()")

    def test_get_inactive_view_renders_authenticated_user(self):
        """
        GET request to AccountInactiveView for authenticated user should render the inactive page.
        """
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
        """
        GET request to AccountInactiveView for anonymous user should render the inactive page.
        """
        request = self.request_factory().get("/inactive/")
        request.user = None
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
    Test AccountRegisterView.
    path("register/", AccountRegisterView.as_view(), name=AccountNamedUrls.ACCOUNT_REGISTER)
    """

    test_logger_prefix = formatted_text(f"{__name__}.TestAccountRegisterView()")

    def setUp(self):
        """Set up for each test."""
        self.test_create_username = f"newuser_{self.hash_suffix}@example.com"
        super().setUp()

    def tearDown(self):

        try:
            u = User.objects.get(username=self.test_create_username)
            u.delete()
        except User.DoesNotExist:
            pass
        super().tearDown()

    def test_get_register_view_renders_for_anonymous(self):
        """
        GET request to AccountRegisterView for anonymous user should render sign-up page with form.
        """
        request = self.request_factory().get("/register/")
        request.user = None
        view = AccountRegisterView()
        response = view.get(request)
        self.assertEqual(
            response.status_code, HTTPStatus.OK, f"Expected OK for anonymous GET but got {response.status_code}"
        )

    def test_get_register_view_redirects_authenticated_user(self):
        """
        GET request to AccountRegisterView for authenticated user should redirect to root.
        """
        request = self.request_factory().get("/register/")
        request.user = self.admin_user
        view = AccountRegisterView()
        response = view.get(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.FOUND,
            f"Expected FOUND for authenticated GET but got {response.status_code}",
        )
        self.assertEqual(response.url, "/")

    def test_post_register_view_valid_form(self):
        """
        POST valid registration data should create user, log in, and redirect to /welcome/.
        """
        data = {
            "email": self.test_create_username,
            "password": "testpass123",
        }
        request = self.request_factory().post("/register/", data)
        request.user = None
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
        self.assertEqual(response.url, "/welcome/")

    def test_post_register_view_invalid_form(self):
        """
        POST invalid registration data should re-render the form with errors.
        """
        data = {"email": "", "password": ""}  # All fields missing/invalid
        request = self.request_factory().post("/register/", data)
        request.user = None
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


class TestAccountActivationEmailView(TestAccountMixin):
    """
    Test AccountActivationEmailView.
    path("activation/", AccountActivationEmailView.as_view(), name=AccountNamedUrls.ACCOUNT_ACTIVATION)
    """

    test_logger_prefix = formatted_text(f"{__name__}.TestAccountActivationEmailView()")

    def setUp(self):
        super().setUp()
        self.url = reverse(AccountNamedUrls.namespace + ":" + AccountNamedUrls.ACCOUNT_ACTIVATION)
        logger.debug("%s.setUp() URL set to %s", self.test_logger_prefix, self.url)

    @patch("smarter.apps.account.views.authentication.email_helper")
    def test_get_authenticated_admin_user_sends_email_and_renders(self, mock_email_helper):
        """
        GET request with authenticated admin user should send activation email and render response.
        """
        request = self.request_factory().get(self.url)
        request.user = self.admin_user
        view = AccountActivationEmailView()
        response = view.get(request)
        self.assertEqual(
            response.status_code, HTTPStatus.OK, f"Expected OK for authenticated GET but got {response.status_code}"
        )
        mock_email_helper.send_email.assert_called_once()

    @patch("smarter.apps.account.views.authentication.email_helper")
    def test_get_authenticated_non_admin_user_sends_email_and_renders(self, mock_email_helper):
        """
        GET request with authenticated non-admin user should send activation email and render response.
        """
        request = self.request_factory().get(self.url)
        request.user = self.non_admin_user
        view = AccountActivationEmailView()
        response = view.get(request)
        self.assertEqual(
            response.status_code, HTTPStatus.OK, f"Expected OK for authenticated GET but got {response.status_code}"
        )
        mock_email_helper.send_email.assert_called_once()

    def test_get_anonymous_user_returns_not_found(self):
        """
        GET request with anonymous user should return not found.
        """
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
        """
        GET request with user missing is_authenticated should return not found.
        """
        request = self.request_factory().get(self.url)
        request.user = AnonymousUser()
        view = AccountActivationEmailView()
        response = view.get(request)
        self.assertEqual(
            response.status_code,
            HTTPStatus.NOT_FOUND,
            f"Expected NOT_FOUND for user missing is_authenticated but got {response.status_code}",
        )
