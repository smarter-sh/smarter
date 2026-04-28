"""Django context processors for account/base.html"""

import logging

from django.conf import settings
from django.urls import reverse

from smarter.apps.account.urls import AccountNamedUrls
from smarter.common.utils import is_authenticated_request

from .models import UserProfile

logger = logging.getLogger(__name__)


def base(request):
    """Base context processor for templates that inherit from account/base.html"""
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
            "forgot_password_url": reverse(AccountNamedUrls.ACCOUNT_PASSWORD_RESET_REQUEST),
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
