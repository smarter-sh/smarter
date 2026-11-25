"""
Custom authentication backends for hosted Smarter platforms.

Includes payment and account status verification.

To verify subscription status, the platform calls the Account Manager:

.. code-block:: bash

    curl 'https://api.am.smarter.sh/accounts/subscription-status/' \
      -H 'Authorization: Platform <the platform key>' \
      -H 'X-Client-Domain: platform.smarter.sh' \
      -H 'X-Client-Username: <username>' \
      -H 'X-Client-Email: <email>'

The platform key, ``smarter_settings.account_manager_api_key``, identifies the platform to the
Account Manager, which issues one per platform. The username and email address together identify
the user, so that another person with the same username can't be mistaken for them. Without a
key, the platform asks without one, which the Account Manager answers only until it requires keys.

It returns HTTP 200 if the subscription is active, and a 4xx status otherwise. Only that
answer is cached (:func:`subscription_status_code`); a failure is never cached.
"""

from http import HTTPStatus
from typing import Optional

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
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

logger = logging.getSmarterLogger(__name__)

USERNAME = "username"
# the account app's url name, in its namespace: a url name alone isn't found.
INACTIVE_ACCOUNT_REDIRECT_URL = f"{account_namespace}:account_inactive"
SUBSCRIPTION_STATUS_API_URL = f"https://api.am.{smarter_settings.platform_root_domain}/accounts/subscription-status/"
"""
API endpoint to verify subscription status.

see https://github.com/smarter-sh/account-manager
"""


ACCOUNT_MANAGER_AUTH_SCHEME = "Platform"
"""The ``Authorization`` header's scheme for the platform key."""


def subscription_status_headers(username: str, email: Optional[str]) -> dict[str, str]:
    """
    Return the headers of a subscription status request: who asks, and about whom.

    The platform key is read here, from the settings, and never passed as an argument: arguments
    of the cached :func:`subscription_status_code` are its cache key, and are logged.

    :param username: The user's username.
    :param email: The user's email address, or None.
    :returns: The headers.
    """
    headers = {
        "accept": "application/json",
        "X-Client-Domain": smarter_settings.environment_platform_domain,
        "X-Client-Username": username,
    }
    if email is not None:
        headers["X-Client-Email"] = email
    api_key = smarter_settings.account_manager_api_key
    if api_key is not None:
        headers["Authorization"] = f"{ACCOUNT_MANAGER_AUTH_SCHEME} {api_key.get_secret_value()}"
    return headers


def email_or_none(email: object) -> Optional[str]:
    """
    Return an email address, stripped, or None when there is none.

    :param email: The email address from a user or a provider's user details: a string, or nothing.
    :returns: The address, or None.
    """
    if not isinstance(email, str):
        return None
    stripped = email.strip()
    if not stripped:
        return None
    return stripped


class SubscriptionStatusUnavailable(Exception):
    """The Account Manager's subscription status endpoint answered with a server error."""


@cache_results()
def subscription_status_code(username: str, email: Optional[str] = None) -> int:
    """
    Return the Account Manager's http status for a user's subscription: 200 if it is active.

    Only this call is cached, and only its answers: a transport error or a server error raises,
    so that it is never cached, and the next sign-in asks again. Cheaper checks, and the waffle
    switch, run before it in :func:`verify_payment_status`, uncached, so that a change to them
    applies at once.

    :param username: The user's username. It is part of the cache key, so it must be the string, not the User.
    :param email: The user's email address, or None. Also part of the cache key.
    :returns: The http status code, 200 or a 4xx.
    :raises requests.RequestException: If the endpoint can't be reached.
    :raises SubscriptionStatusUnavailable: If the endpoint answers with a 5xx status.
    """
    headers = subscription_status_headers(username, email)
    response = requests.get(SUBSCRIPTION_STATUS_API_URL, headers=headers, timeout=5)
    status_code = response.status_code
    logger.info(
        "Subscription status API response for user %s: %s",
        username,
        status_code,
    )
    if status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        raise SubscriptionStatusUnavailable(f"subscription status api answered {status_code}")
    return status_code


def verify_payment_status(username: str, email: Optional[str] = None) -> bool:
    """
    Verify the payment status of a user with the Account Manager's subscription status endpoint.

    Returns True if the subscription is active, False otherwise. Superusers, and every user
    while multitenant authentication is off, pass without a call. When the status can't be
    checked, it fails open and returns True, to avoid blocking access due to transient issues.
    Only the endpoint's answer is cached, by :func:`subscription_status_code`. The two early
    returns don't name the user in the log: a username is often a person's name.

    :param username: The user's username.
    :param email: The user's email address, or None. The Account Manager requires it from a platform
        with a key, and answers 400, an inactive subscription, without it.
    :returns: True if the subscription is active, or the status can't be checked.
    """
    # check to see if multitenant authentication is enabled
    if not switch_is_active(SmarterWaffleSwitches.ENABLE_MULTITENANT_AUTHENTICATION):
        logger.info(
            "Multitenant authentication is disabled; skipping the payment status check. You can enable multitenant authentication by activating the corresponding waffle switch in the Django admin console.",
        )
        return True

    # Superusers are always allowed access
    is_superuser = User.objects.filter(username=username, is_superuser=True, is_active=True).exists()
    if is_superuser:
        logger.info(
            "the user is a superuser; skipping the payment status check.",
        )
        return True

    try:
        status_code = subscription_status_code(username, email)
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
        "%s error occurred while verifying payment status for user %s: %s",
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
        logger.debug("Retrieved user details: %s", details)
        if details is None:
            # authentication failed, so no point in checking payment status
            return None
        if not isinstance(details, dict):
            # this should never happen, but log just in case
            logger.error(
                "could not verify payment status. Expected user details to be a dictionary, got %s.",
                type(details),
            )
            return details
        username = details.get(USERNAME)
        if not isinstance(username, str) or not username:
            # without a username there is nothing to check; verify_payment_status() fails open, and so does this.
            logger.warning(
                "the user details have no username, so the payment status is not checked.",
            )
            return details
        email = email_or_none(details.get("email"))
        if verify_payment_status(username, email):
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
                "Skipping payment status check for user %s in local environment.",
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
            # the authenticated user's own username and email: the username argument is whatever the
            # caller passed, which can be a User, and subscription_status_code() is cached by its arguments.
            # a custom user model may have no email field, so it is read with getattr().
            email = email_or_none(getattr(user, "email", None))
            if not verify_payment_status(user.get_username(), email):
                if request is not None:
                    messages.error(request, _("Your subscription is not active. Please check your payment status."))
                return redirect(INACTIVE_ACCOUNT_REDIRECT_URL)
        return user
