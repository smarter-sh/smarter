# -*- coding: utf-8 -*-
"""Account utilities."""
from typing import Type

from django.contrib.auth import get_user_model

from .models import Account, UserProfile


User = get_user_model()
UserType = Type[User]


def account_for_user(user) -> Account:
    """
    Locates the account for a given user, or None if no account exists.
    """
    try:
        user_profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return None
    return user_profile.account


def account_admin_user(account: Account) -> UserType:
    """
    Returns the account admin user for the given account.
    """

    try:
        user_profile = UserProfile.objects.filter(account=account, user__is_staff=True).order_by("pk").first()
        return user_profile.user
    except UserProfile.DoesNotExist as e:
        raise ValueError(f"No account admin user found for account {account.account_number}.") from e
