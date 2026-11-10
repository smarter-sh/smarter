"""URL configuration for the web platform."""

from django.urls import path

from smarter.apps.dashboard.views.console_app import ConsoleAppView
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.utils import to_snake_case
from smarter.lib import logging

from .const import namespace
from .password_reset import PASSWORD_RESET_LINK_NAME
from .views.email import EmailSlackInvitationView, EmailWelcomeView
from .views.unsubscribe import AccountUnsubscribeView

logger = logging.getLogger(__name__)


class AccountReverseNames:
    """
    Class to hold named URL patterns for the account app.

    The names follow the convention ``account_<view_name>``, and are reversed as
    ``account:<name>``. Sign-in, sign-out, registration and the password urls are
    mounted at the root of the console urlconf, :mod:`smarter.urls.console`.

    The inactive account, already associated and activation pages are the single-page console's
    (:class:`~smarter.apps.dashboard.views.console_app.ConsoleAppView`). They keep their names, which the
    social sign-in pipeline and the activation email reverse.

    .. usage-example::

      .. html::

      <a href="{% url 'account:account_inactive' %}">Account inactive</a>
    """

    namespace = namespace

    ACCOUNT_ALREADY_ASSOCIATED = "account_already_associated"
    ACCOUNT_ACTIVATE = "account_activate"
    ACCOUNT_INACTIVE = "account_inactive"
    ACCOUNT_PASSWORD_RESET_REQUEST = "account_password_reset_request"
    PASSWORD_RESET_LINK = PASSWORD_RESET_LINK_NAME

    unsubscribe = to_snake_case(AccountUnsubscribeView.__name__)
    email_welcome = to_snake_case(EmailWelcomeView.__name__)
    email_slack_invitation = to_snake_case(EmailSlackInvitationView.__name__)


app_name = namespace
urlpatterns = [
    # the pages of the single-page console. See smarter.apps.dashboard.views.console_app.
    path("already-associated/", ConsoleAppView.as_view(), name=AccountReverseNames.ACCOUNT_ALREADY_ASSOCIATED),
    path("inactive/", ConsoleAppView.as_view(), name=AccountReverseNames.ACCOUNT_INACTIVE),
    path("activate/<uidb64>/<token>/", ConsoleAppView.as_view(), name=AccountReverseNames.ACCOUNT_ACTIVATE),
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
