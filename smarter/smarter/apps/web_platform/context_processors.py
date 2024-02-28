# -*- coding: utf-8 -*-
"""Django context processors for base.html"""
from datetime import datetime

from smarter.__version__ import __version__
from smarter.apps.account.models import Account, UserProfile


def base(request):
    current_year = datetime.now().year
    base_keys = {
        "smarter_version": __version__,
        "footer_message": f"Copyright {current_year}. All rights reserved.",
    }
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.get(user=request.user)
        account = Account.objects.get(id=user_profile.account_id)
        user_keys = {
            "user_name": request.user.username,
            "user_first_name": request.user.first_name,
            "user_last_name": request.user.last_name,
            "user_email": request.user.email,
            "my_plugins": 12,
            "django_admin_title": "Account Administration - " + account.company_name,
        }
        return {**base_keys, **user_keys}
    return base_keys
