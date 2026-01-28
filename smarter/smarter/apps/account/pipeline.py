# pylint: disable=unused-argument
"""
Authentication pipeline functions for account management.
"""

import logging

import requests
from django.shortcuts import redirect
from social_core.exceptions import AuthAlreadyAssociated
from social_django.middleware import SocialAuthExceptionMiddleware

from smarter.apps.account.models import UserProfile
from smarter.apps.account.urls import AccountNamedUrls
from smarter.common.helpers.console_helpers import formatted_text

logger = logging.getLogger(__name__)
logger_prefix = formatted_text(__name__)


class SmarterSocialAuthExceptionMiddleware(SocialAuthExceptionMiddleware):
    """
    Custom Social Auth Exception Middleware to handle specific exceptions
    during the social authentication pipeline.
    """

    def process_exception(self, request, exception):
        # strategy = getattr(request, "social_strategy", None)
        # if strategy is None or self.raise_exception(request, exception):
        #     return None

        if isinstance(exception, AuthAlreadyAssociated):
            logger.warning(
                "%s SmarterSocialAuthExceptionMiddleware: AssociationAlreadyExists for request=%s, exception=%s",
                logger_prefix,
                request,
                exception,
            )
            return redirect(AccountNamedUrls.namespace + ":" + AccountNamedUrls.ACCOUNT_ALREADY_ASSOCIATED)
        return super().process_exception(request, exception)


def create_user(strategy, details, backend, *args, user=None, **kwargs):
    """
    Custom user creation function to replace the default one in the
    social auth pipeline. This allows for additional customization
    during user creation if needed.

    expecting details to contain the following:
    details={
        'username': 'lpm0073',
        'email': 'lpm0073@gmail.com',
        'fullname': 'Lawrence McDaniel',
        'first_name': 'Lawrence',
        'last_name': 'McDaniel'
    }

    """
    if user:
        logger.debug("%s.create_user() User already exists: %s", logger_prefix, user)
        return {"is_new": False, "user": user}

    fields = {
        "username": details.get("username"),
        "email": details.get("email"),
        "first_name": details.get("first_name"),
        "last_name": details.get("last_name"),
    }
    if not fields:
        logger.error(
            "%s.create_user() No fields available to create user. Received the following: strategy=%s, details=%s, backend=%s, user=%s, kwargs=%s",
            logger_prefix,
            strategy,
            details,
            backend,
            user,
            kwargs,
        )
        return {"is_new": False, "user": None}

    fields["is_active"] = False  # Ensure the user is inactive upon creation
    user = strategy.create_user(**fields)
    logger.info("%s.create_user() Created new user: %s", logger_prefix, user)
    return {
        "is_new": True,
        "user": user,
    }


def user_details(strategy, details, backend, *args, user=None, **kwargs):
    """
    Custom user details update function to replace the default one in the
    social auth pipeline. This allows for updating additional fields
    during user details update if needed.

    """
    if user is None:
        logger.debug("%s.user_details() No user provided to update.", logger_prefix)
        return

    user_profile: UserProfile

    changed = False
    if details.get("first_name") and user.first_name != details["first_name"]:
        user.first_name = details["first_name"]
        changed = True
    if details.get("last_name") and user.last_name != details["last_name"]:
        user.last_name = details["last_name"]
        changed = True
    if details.get("email") and user.email != details["email"]:
        user.email = details["email"]
        changed = True

    if changed:
        user.save()
        logger.info("%s.user_details() Updated user details for: %s", logger_prefix, user)
    else:
        logger.debug("%s.user_details() No changes detected for user: %s", logger_prefix, user)

    profile_image_url = kwargs.get("response", {}).get("picture")
    if not profile_image_url:
        return None

    # Validate the profile image URL by making a HEAD request
    try:
        response = requests.head(profile_image_url, timeout=1)
        if response.status_code != 200:
            logger.error(
                "%s.user_details() Failed to fetch profile image from URL: %s. Status code: %s",
                logger_prefix,
                profile_image_url,
                response.status_code,
            )
            return None
    except requests.RequestException as e:
        logger.error(
            "%s.user_details() Exception occurred while fetching profile image from URL: %s. Exception: %s",
            logger_prefix,
            profile_image_url,
            e,
        )
        return None

    try:
        user_profile = UserProfile.objects.get(user=user)
        if user_profile.profile_image_url != profile_image_url:
            user_profile.profile_image_url = profile_image_url
            user_profile.save()
            logger.info("%s.user_details() Updated profile image URL for user: %s", logger_prefix, user)
    except UserProfile.DoesNotExist:
        logger.error("%s.user_details() No UserProfile found for user: %s. This is a bug.", logger_prefix, user)


def redirect_inactive_account(strategy, details, *args, user=None, **kwargs):
    """
    A pipeline function to redirect users with inactive accounts
    (e.g., payment inactive) to a custom page.
    This is used in settings.SOCIAL_AUTH_PIPELINE for the following:

    1. when running a multitenant setup and the account is inactive (e.g., payment inactive),
       redirect the user to a custom page instead of allowing login.

    2. when a user.is_active is False, redirect to a custom page.


    """
    logger.debug(
        "%s.redirect_inactive_account() called with strategy=%s, details=%s, user=%s, kwargs=%s",
        logger_prefix,
        strategy,
        details,
        user,
        kwargs,
    )
    request = strategy.request if hasattr(strategy, "request") else None
    if request and request.session.get("account_status") == "inactive":
        # clear the flag so it doesn't persist
        del request.session["account_status"]
        return redirect(AccountNamedUrls.namespace + ":" + AccountNamedUrls.ACCOUNT_INACTIVE)

    # Self-onboarded user who registered with oauth but their account is
    # not active.
    if user and hasattr(user, "is_active") and not user.is_active:
        return redirect(AccountNamedUrls.namespace + ":" + AccountNamedUrls.ACCOUNT_INACTIVE)

    # Continue the pipeline as normal
    return None
