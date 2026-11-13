"""
Custom authentication backends for hosted Smarter platforms.

Includes payment and account status verification.

To verify subscription status, use the following API call:

.. code-block:: bash

    curl -X 'GET' \
      'https://api.am.smarter.sh/accounts/subscription-status/' \
      -H 'accept: application/json' \
      -H 'X-Client-Domain: platform.smarter.sh' \
      -H 'X-Client-Username: <username>'

It returns HTTP 200 if the subscription is active, and a 4xx status otherwise. Only that
answer is cached (:func:`subscription_status_code`); a failure is never cached.
"""

from http import HTTPStatus

import requests
from cache_results import cache_results
from django.contrib import messages
from django.contrib.auth.backends import ModelBackend
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from requests.exceptions import RequestException, Timeout
from social_core.backends.github import GithubOAuth2
from social_core.backends.google import GoogleOAuth2

from smarter.apps.account.const import namespace as account_namespace
from smarter.apps.account.models import User
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

logger = logging.getLogger(__name__)
logger_prefix = SmarterFormattedText.text(__name__)

USERNAME = "username"
# the account app's url name, in its namespace: a url name alone isn't found.
INACTIVE_ACCOUNT_REDIRECT_URL = f"{account_namespace}:account_inactive"
SUBSCRIPTION_STATUS_API_URL = f"https://api.am.{smarter_settings.root_domain}/accounts/subscription-status/"
"""
API endpoint to verify subscription status.

see https://github.com/smarter-sh/account-manager
"""


class SubscriptionStatusUnavailable(Exception):
    """The Account Manager's subscription status endpoint answered with a server error."""


@cache_results()
def subscription_status_code(username: str) -> int:
    """
    Return the Account Manager's http status for a user's subscription: 200 if it is active.

    Only this call is cached, and only its answers: a transport error or a server error raises,
    so that it is never cached, and the next sign-in asks again. Cheaper checks, and the waffle
    switch, run before it in :func:`verify_payment_status`, uncached, so that a change to them
    applies at once.

    :param username: The user's username. It is the cache key, so it must be the string, not the User.
    :returns: The http status code, 200 or a 4xx.
    :raises requests.RequestException: If the endpoint can't be reached.
    :raises SubscriptionStatusUnavailable: If the endpoint answers with a 5xx status.
    """
    headers = {
        "accept": "application/json",
        "X-Client-Domain": smarter_settings.environment_platform_domain,
        "X-Client-Username": username,
    }
    response = requests.get(SUBSCRIPTION_STATUS_API_URL, headers=headers, timeout=5)
    status_code = response.status_code
    logger.info(
        "%s.subscription_status_code() Subscription status API response for user %s: %s",
        logger_prefix,
        username,
        status_code,
    )
    if status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        raise SubscriptionStatusUnavailable(f"subscription status api answered {status_code}")
    return status_code


def verify_payment_status(username: str) -> bool:
    """
    Verify the payment status of a user with the Account Manager's subscription status endpoint.

    Returns True if the subscription is active, False otherwise. Superusers, and every user
    while multitenant authentication is off, pass without a call. When the status can't be
    checked, it fails open and returns True, to avoid blocking access due to transient issues.
    Only the endpoint's answer is cached, by :func:`subscription_status_code`.

    :param username: The user's username.
    :returns: True if the subscription is active, or the status can't be checked.
    """
    # check to see if multitenant authentication is enabled
    if not switch_is_active(SmarterWaffleSwitches.ENABLE_MULTITENANT_AUTHENTICATION):
        logger.info(
            "%s.verify_payment_status() Multitenant authentication is disabled; skipping payment status check for user %s. You can enable multitenant authentication by activating the corresponding waffle switch in the Django admin console.",
            logger_prefix,
            username,
        )
        return True

    # Superusers are always allowed access
    is_superuser = User.objects.filter(username=username, is_superuser=True, is_active=True).exists()
    if is_superuser:
        logger.info(
            "%s.verify_payment_status() User %s is a superuser; skipping payment status check.", logger_prefix, username
        )
        return True

    try:
        status_code = subscription_status_code(username)
    except Timeout as timeout_err:
        log_status_error("Timeout", username, timeout_err)
        return True
    except (RequestException, SubscriptionStatusUnavailable) as request_err:
        log_status_error(type(request_err).__name__, username, request_err, stack_info=True)
        return True
    # pylint: disable=broad-except
    except Exception as e:
        log_status_error("Unexpected", username, e, stack_info=True)
        return True

    is_active = status_code == HTTPStatus.OK
    return is_active


def log_status_error(err_type: str, username: str, err: Exception, stack_info: bool = False) -> None:
    """
    Log an error of the subscription status API call.

    :param err_type: The kind of error, e.g. ``Timeout``.
    :param username: The user whose status was checked.
    :param err: The exception.
    :param stack_info: Whether to log the stack.
    """
    logger.error(
        "%s.verify_payment_status() %s error occurred while verifying payment status for user %s: %s",
        logger_prefix,
        err_type,
        username,
        err,
        stack_info=stack_info,
    )


class PaymentVerifiedUserDetailsMixin:
    """
    Verify the hosted platform payment status of a user who signs in with an OAuth2 provider.

    Put it before the provider's backend class, so that its :meth:`get_user_details` runs first
    and calls the backend's own through ``super()``.
    """

    def allow_unpaid_user(self, details: dict) -> bool:
        """
        Return whether a user whose subscription is not paid may still sign in.

        :param details: The user details from the provider.
        :returns: False. A subclass can override it.
        """
        return False

    def get_user_details(self, response):
        """
        Return the user's details from the provider, or None if their hosted platform subscription is not paid.

        An unpaid user gets an error message, and their session's ``account_status`` is set to
        ``inactive``, unless :meth:`allow_unpaid_user` allows them.

        :param response: The provider's user data.
        :returns: The user details, or None.
        """
        # the backend that this mixin precedes in the MRO, e.g. GoogleOAuth2, defines get_user_details().
        details = super().get_user_details(response)  # type: ignore[misc]
        logger.debug("%s.get_user_details() Retrieved user details: %s", logger_prefix, details)
        if details is None:
            # authentication failed, so no point in checking payment status
            return None
        if not isinstance(details, dict):
            # this should never happen, but log just in case
            logger.error(
                "%s.get_user_details() could not verify payment status. Expected user details to be a dictionary, got %s.",
                logger_prefix,
                type(details),
            )
            return details
        username = details.get(USERNAME)
        if not isinstance(username, str) or not username:
            # without a username there is nothing to check; verify_payment_status() fails open, and so does this.
            logger.warning(
                "%s.get_user_details() the user details have no username, so the payment status is not checked.",
                logger_prefix,
            )
            return details
        if verify_payment_status(username):
            return details
        if self.allow_unpaid_user(details):
            return details
        request = getattr(self, "strategy", None)
        if request and hasattr(request, "request"):
            messages.error(request.request, _("Your subscription is not active. Please check your payment status."))
            request.request.session["account_status"] = "inactive"
        return None


class GoogleOAuth2Multitenant(PaymentVerifiedUserDetailsMixin, GoogleOAuth2):
    """Custom Google OAuth2 backend that also verifies payment status of the hosted platform."""


class GithubOAuth2Multitenant(PaymentVerifiedUserDetailsMixin, GithubOAuth2):
    """
    Custom GitHub OAuth2 backend that also verifies payment status of the hosted platform.

    The payment check is skipped in the local environment.
    """

    def allow_unpaid_user(self, details: dict) -> bool:
        """
        Return whether a user whose subscription is not paid may still sign in: only in the local environment.

        :param details: The user details from GitHub.
        :returns: True in the local environment.
        """
        if smarter_settings.environment == SmarterEnvironments.LOCAL:
            logger.warning(
                "%s.get_user_details() Skipping payment status check for user %s in local environment.",
                logger_prefix,
                details.get(USERNAME),
            )
            return True
        return False


class DjangoModelBackendMultitenant(ModelBackend):
    """Custom Django ModelBackend that also verifies payment status of the hosted platform."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate with a username and password, then check the user's hosted platform subscription.

        :param request: The request, or None.
        :param username: The username.
        :param password: The password.
        :param kwargs: Passed to Django's ``ModelBackend.authenticate()``.
        :returns: The user, None if the credentials are wrong, or a redirect to the inactive account
            page if the subscription is not paid.
        """
        user = super().authenticate(request, username, password, **kwargs)
        if user:
            # the authenticated user's own username: the username argument is whatever the caller
            # passed, which can be a User, and verify_payment_status() is cached by its argument.
            if not verify_payment_status(user.get_username()):
                if request is not None:
                    messages.error(request, _("Your subscription is not active. Please check your payment status."))
                return redirect(INACTIVE_ACCOUNT_REDIRECT_URL)
        return user
