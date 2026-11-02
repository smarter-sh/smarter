"""URL configuration for the web platform."""

from django.urls import include, path

from smarter.apps.account.views.dashboard import urls as account_dashboard_urls
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.utils import to_snake_case
from smarter.lib import logging

from .const import namespace
from .views.authentication import (
    AccountActivateView,
    AccountActivationEmailView,
    AccountDeactivateView,
    AccountInactiveView,
    AccountRegisterView,
    LoginView,
    LogoutView,
    SocialAuthAlreadyAssociatedView,
)
from .views.dashboard.api_keys import APIKeyListView
from .views.dashboard.users import UsersView, UserView
from .views.email import EmailSlackInvitationView, EmailWelcomeView
from .views.unsubscribe import AccountUnsubscribeView

logger = logging.getLogger(__name__)


class AccountReverseNames:
    """
    Class to hold named URL patterns for the account app.

    This class provides constants for all named URL patterns used in the account dashboard views.
    The names follow the convention: 'account_<view_name>'.
    These are referenced in Django templates as 'reverse' or 'url' tags.

    .. usage-example::

      .. html::

      <a href="{% url 'dashboard_account_dashboard_overview' %}">Go to Dashboard Overview</a>
    """

    namespace = namespace

    API_KEYS_LIST = "api_keys_list"
    ACCOUNT_ALREADY_ASSOCIATED = "account_already_associated"
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

    unsubscribe = to_snake_case(AccountUnsubscribeView.__name__)
    email_welcome = to_snake_case(EmailWelcomeView.__name__)
    email_slack_invitation = to_snake_case(EmailSlackInvitationView.__name__)


app_name = namespace
urlpatterns = [
    path(
        "already-associated/",
        SocialAuthAlreadyAssociatedView.as_view(),
        name=AccountReverseNames.ACCOUNT_ALREADY_ASSOCIATED,
    ),
    # mcdaniel disabled: it redirected to the deprecated Account UI. See smarter.apps.account.views.dashboard.urls.
    # path(
    #     "",
    #     RedirectView.as_view(url="/dashboard/account/dashboard/", permanent=False),
    #     name="dashboard_account_dashboard",
    # ),
    path("api-keys/", APIKeyListView.as_view(), name=AccountReverseNames.API_KEYS_LIST),
    path("login/", LoginView.as_view(), name=AccountReverseNames.ACCOUNT_LOGIN),
    path("logout/", LogoutView.as_view(), name=AccountReverseNames.ACCOUNT_LOGOUT),
    path("inactive/", AccountInactiveView.as_view(), name=AccountReverseNames.ACCOUNT_INACTIVE),
    path("dashboard/", include(account_dashboard_urls)),
    # account lifecycle
    path("register/", AccountRegisterView.as_view(), name=AccountReverseNames.ACCOUNT_REGISTER),
    path("activation/", AccountActivationEmailView.as_view(), name=AccountReverseNames.ACCOUNT_ACTIVATION),
    path("activate/<uidb64>/<token>/", AccountActivateView.as_view(), name=AccountReverseNames.ACCOUNT_ACTIVATE),
    path("deactivate/", AccountDeactivateView.as_view(), name=AccountReverseNames.ACCOUNT_DEACTIVATE),
    path("users/", UsersView.as_view(), name=AccountReverseNames.ACCOUNT_USERS),
    path("user/<int:user_id>/", UserView.as_view(), name=AccountReverseNames.ACCOUNT_USER),
    path("unsubscribe/<str:token>/", AccountUnsubscribeView.as_view(), name=AccountReverseNames.unsubscribe),
]

if smarter_settings.environment == SmarterEnvironments.LOCAL:
    urlpatterns += [
        path("email/welcome/<first_name>/", EmailWelcomeView.as_view(), name=AccountReverseNames.email_welcome),
        path(
            "email/slack-invitation/<first_name>/",
            EmailSlackInvitationView.as_view(),
            name=AccountReverseNames.email_slack_invitation,
        ),
    ]
    logger_prefix = SmarterFormattedText.text(__name__)
    logger.debug("%s added the email preview URL patterns to Account app URLs.", logger_prefix)
