"""URL configuration for the web platform."""

from django.urls import include, path
from django.views.generic.base import RedirectView

from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterEnvironments

from .const import namespace
from .views.authentication import (
    AccountActivateView,
    AccountActivationEmailView,
    AccountDeactivateView,
    AccountRegisterView,
    LoginView,
    LogoutView,
)
from .views.dashboard.api_keys import APIKeyListView
from .views.password_management import (
    PasswordConfirmView,
    PasswordResetRequestView,
    PasswordResetView,
)


class AccountNamedUrls:
    """
    Class to hold named URL patterns for the account app.
    This class provides constants for all named URL patterns used in the account dashboard views.
    The names follow the convention: 'account_<view_name>'.
    These are referenced in Django templates as 'reverse' or 'url' tags.

    .. usage-example::

      .. html::

      <a href="{% url 'dashboard_account_dashboard_overview' %}">Go to Dashboard Overview</a>

    """

    API_KEYS_LIST = "api_keys_list"
    ACCOUNT_LOGIN = "account_login"
    ACCOUNT_LOGOUT = "account_logout"
    ACCOUNT_REGISTER = "account_register"
    ACCOUNT_ACTIVATION = "account_activation"
    ACCOUNT_ACTIVATE = "account_activate"
    ACCOUNT_DEACTIVATE = "account_deactivate"
    ACCOUNT_PASSWORD_RESET_REQUEST = "account_password_reset_request"
    ACCOUNT_PASSWORD_CONFIRM = "account_password_confirm"
    PASSWORD_RESET_LINK = "password_reset_link"


app_name = namespace
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
]

if smarter_settings.environment == SmarterEnvironments.LOCAL:
    from .views.email import EmailWelcomeView

    urlpatterns.append(path("email/welcome/<first_name>/", EmailWelcomeView.as_view(), name="welcome"))
