# -*- coding: utf-8 -*-
"""Account utilities."""

from django.contrib.auth.models import User

from smarter.apps.account.models import Account, UserProfile


def account_for_user(user: User) -> Account:
    """
    Locates the account for a given user, or None if no account exists.
    """
    try:
        user_profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return None
    return user_profile.account
