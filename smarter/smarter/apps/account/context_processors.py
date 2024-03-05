# -*- coding: utf-8 -*-
"""Django context processors for account/base.html"""
from django.conf import settings

from smarter.apps.account.models import Account, UserProfile


def base(request):
    """Base context processor for templates that inherit from account/base.html"""
    account_authentication = {
        "account_authentication": {
            "login_url": settings.LOGIN_URL,
            "logout_url": "/logout/",
            "registration_url": "/register/",
            "password_reset_url": "/account/reset-password/",
            "new_password_url": "/account/new-password/",
        }
    }
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.get(user=request.user)
        account = Account.objects.get(id=user_profile.account_id)
        account_authenticated = {
            "account_authenticated": {
                "account_authentication_user": request.user,
                "account_authentication_account": account,
            }
        }
        return {**account_authentication, **account_authenticated}
    return account_authentication
