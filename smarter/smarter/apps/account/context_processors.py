"""Django context processors for account/base.html."""

from django.conf import settings

from smarter.apps.account.urls import AccountReverseNames
from smarter.common.utils import is_authenticated_request
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse

from .models import UserProfile

logger = logging.getLogger(__name__)


def base(request):
    """
    Base context processor for templates that inherit from account/base.html.

    Its urls are web console urls, so they are reversed against ``settings.ROOT_URLCONF``, not the urlconf
    that django-hosts activated for the request. A deployed LLMClient's host, whose pages are rendered with
    this processor too, is served by :mod:`smarter.urls.llmclients`, which has none of the console's names.
    """
    account_context = {
        "account": {
            "registration_url": "/register/",
            "welcome_url": "/account/welcome/",
            "deactivate_url": "/account/deactivate/",
        }
    }
    account_authentication_context = {
        "account_authentication": {
            "login_url": settings.LOGIN_URL,
            "logout_url": "/logout/",
            "forgot_password_url": reverse(
                AccountReverseNames.ACCOUNT_PASSWORD_RESET_REQUEST, urlconf=settings.ROOT_URLCONF
            ),
        }
    }
    if is_authenticated_request(request):
        try:
            user_profile = UserProfile.get_cached_object(user=request.user)
        except UserProfile.DoesNotExist:
            user_profile = None
            logger.warning("UserProfile.DoesNotExist: user_profile not found for user %s", request.user)

        account_authenticated_context = {
            "account_authenticated": {
                "user": request.user if request and hasattr(request, "user") else None,
                "account": user_profile.cached_account if user_profile else None,
            }
        }
        return {**account_context, **account_authentication_context, **account_authenticated_context}
    return {**account_context, **account_authentication_context}
