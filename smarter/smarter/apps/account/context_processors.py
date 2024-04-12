# -*- coding: utf-8 -*-
"""Django context processors for account/base.html"""
import logging

from django.conf import settings

from .models import Account, UserProfile


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
            "forgot_password_url": "/account/password-reset-request/",
        }
    }
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            account = Account.objects.get(id=user_profile.account_id)
        except UserProfile.DoesNotExist:
            logger.warning("UserProfile.DoesNotExist: user_profile not found for user %s", request.user)

        account_authenticated_context = {
            "account_authenticated": {
                "user": request.user,
                "account": account or None,
            }
        }
        return {**account_context, **account_authentication_context, **account_authenticated_context}
    return {**account_context, **account_authentication_context}
