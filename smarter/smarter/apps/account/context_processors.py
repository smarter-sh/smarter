# -*- coding: utf-8 -*-
"""Django context processors for account/base.html"""
from django.conf import settings

from smarter.apps.account.models import Account, UserProfile


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
            "password_reset_url": "/account/reset-password/",
            "new_password_url": "/account/new-password/",
        }
    }
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.get(user=request.user)
        account = Account.objects.get(id=user_profile.account_id)
        account_authenticated_context = {
            "account_authenticated": {
                "user": request.user,
                "account": account,
            }
        }
        return {**account_context, **account_authentication_context, **account_authenticated_context}
    return {**account_context, **account_authentication_context}
