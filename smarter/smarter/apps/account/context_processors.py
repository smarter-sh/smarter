"""Django context processors for account/base.html"""

import logging

from django.conf import settings

from .models import UserProfile
from .utils import get_cached_user_profile


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
            "forgot_password_url": "/dashboard/account/password-reset-request/",
        }
    }
    if request.user.is_authenticated:
        try:
            user_profile = get_cached_user_profile(user=request.user)
        except UserProfile.DoesNotExist:
            logger.warning("UserProfile.DoesNotExist: user_profile not found for user %s", request.user)

        account_authenticated_context = {
            "account_authenticated": {
                "user": request.user if request and hasattr(request, "user") else None,
                "account": user_profile.account if user_profile else None,
            }
        }
        return {**account_context, **account_authentication_context, **account_authenticated_context}
    return {**account_context, **account_authentication_context}
