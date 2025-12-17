"""
Custom authentication backends for hosted Smarter platforms.
Includes payment and account status verification.

To verify subscription status, use the following API call:

curl -X 'GET' \
  'https://api.am.smarter.sh/accounts/subscription-status/' \
  -H 'accept: application/json' \
  -H 'X-Client-Domain: platform.smarter.sh' \
  -H 'X-Client-Username: lmcdaniel'

Returns HTTP 200 if the subscription is active. 40x otherwise.
"""

import logging
from http import HTTPStatus

import requests_cache
from django.contrib import messages
from django.contrib.auth.backends import ModelBackend
from requests.exceptions import HTTPError, RequestException, Timeout, TooManyRedirects
from retry_requests import retry
from social_core.backends.github import GithubOAuth2
from social_core.backends.google import GoogleOAuth2

from smarter.common.conf import settings as smarter_settings


logger = logging.getLogger(__name__)

USERNAME = "username"
SUBSCRIPTION_STATUS_API_URL = f"https://api.am.{smarter_settings.root_domain}/accounts/subscription-status/"
request_cache = requests_cache.CachedSession("/tmp/.subscription_status_cache", expire_after=600)  # nosec
retriable_request = retry(request_cache, retries=5, backoff_factor=0.2)


def verify_payment_status(username) -> bool:
    """
    Verify the payment status of a user by making an API call
    to the Account Manager subscription status endpoint.
    Returns True if the subscription is active, False otherwise.
    In case of errors, defaults to returning True to avoid
    blocking access due to transient issues.
    """

    def handle_error(err_type: str, err) -> str:
        """
        Helper function to format error messages.
        """
        return f"{err_type} error occurred while verifying payment status for user {username}: {err}"

    DEFAULT_ERROR_RESPONSE = True
    headers = {
        "accept": "application/json",
        "X-Client-Domain": smarter_settings.environment_platform_domain,
        "X-Client-Username": username,
    }
    try:
        response = retriable_request.get(SUBSCRIPTION_STATUS_API_URL, headers=headers, timeout=5)
        logger.info("Subscription status API response for user %s: %s", username, response.status_code)
        return response.status_code == HTTPStatus.OK
    except Timeout as timeout_err:
        logger.error(handle_error("Timeout", timeout_err))
        return DEFAULT_ERROR_RESPONSE
    except HTTPError as http_err:
        logger.error(handle_error("HTTP", http_err), stack_info=True)
        return DEFAULT_ERROR_RESPONSE
    except ConnectionError as conn_err:
        logger.error(handle_error("Connection", conn_err), stack_info=True)
        return DEFAULT_ERROR_RESPONSE
    except TooManyRedirects as redirects_err:
        logger.error(handle_error("Too many redirects", redirects_err), stack_info=True)
        return DEFAULT_ERROR_RESPONSE
    except RequestException as req_err:
        logger.error(handle_error("Request", req_err), stack_info=True)
        return DEFAULT_ERROR_RESPONSE
    # pylint: disable=broad-except
    except Exception as e:
        logger.error(
            "Unexpected error occurred while verifying payment status for user %s: %s", username, e, stack_info=True
        )
        return DEFAULT_ERROR_RESPONSE


class GoogleOAuth2Hosted(GoogleOAuth2):
    """
    Custom Google OAuth2 backend that also verifies
    payment status of the hosted platform.
    """

    def get_user_details(self, response):
        details = super().get_user_details(response)
        if details is None:
            # authentication failed, so not point in checking payment status
            return None
        if not isinstance(details, dict):
            # this should never happen, but log just in case
            logger.error(
                "could not verify payment status. Expected user details to be a dictionary, got %s.", type(details)
            )
            return details
        if verify_payment_status(details.get(USERNAME)):
            return details
        # Optionally, attach a message to the request if available
        request = getattr(self, "strategy", None)
        if request and hasattr(request, "request"):
            messages.error(request.request, "Your subscription is not active. Please check your payment status.")
        return None


class GithubOAuth2Hosted(GithubOAuth2):
    """
    Custom GitHub OAuth2 backend that also verifies
    payment status of the hosted platform.
    """

    def get_user_details(self, response):
        details = super().get_user_details(response)
        if details is None:
            # authentication failed, so not point in checking payment status
            return None
        if not isinstance(details, dict):
            # this should never happen, but log just in case
            logger.error(
                "could not verify payment status. Expected user details to be a dictionary, got %s.", type(details)
            )
            return details
        if verify_payment_status(details.get(USERNAME)):
            return details
        request = getattr(self, "strategy", None)
        if request and hasattr(request, "request"):
            messages.error(request.request, "Your subscription is not active. Please check your payment status.")
        return None


class DjangoModelBackendHosted(ModelBackend):
    """
    Custom Django ModelBackend that also verifies
    payment status of the hosted platform.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(request, username, password, **kwargs)
        username = username or kwargs.get(USERNAME)
        if user and username:
            if not verify_payment_status(username):
                if request is not None:
                    messages.error(request, "Your subscription is not active. Please check your payment status.")
                return None
        return user
