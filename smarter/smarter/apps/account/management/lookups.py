"""
Lookups for the account app's management commands.

Each function finds one Account, User or UserProfile from a command's options, and raises a
:class:`~django.core.management.base.CommandError` with a message that tells the operator what to
do when there is none, or more than one. Django prints a ``CommandError`` as one line, without a
stack trace, and exits with status 1.
"""

from typing import Optional

from django.core.management.base import CommandError

from smarter.apps.account.models import Account, User, UserProfile


def get_account(account_number: Optional[str] = None, company_name: Optional[str] = None) -> Account:
    """
    Return the account with the account number, or else the company name.

    :param account_number: the account number, e.g. ``3141-5926-5359``.
    :param company_name: the account's company name.
    :returns: the account.
    :raises CommandError: if neither is given, or no account, or more than one, matches.
    """
    if account_number:
        lookup, description = {"account_number": account_number}, f"account number {account_number}"
    elif company_name:
        lookup, description = {"company_name": company_name}, f"company name {company_name}"
    else:
        raise CommandError("Provide an --account_number or a --company_name.")
    try:
        return Account.objects.get(**lookup)
    except Account.DoesNotExist as e:
        raise CommandError(f"There is no account with the {description}.") from e
    except Account.MultipleObjectsReturned as e:
        raise CommandError(f"Several accounts have the {description}. Use --account_number instead.") from e


def get_user(username: str) -> User:
    """
    Return the user with the username.

    :param username: the username.
    :returns: the user.
    :raises CommandError: if there is no such user.
    """
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist as e:
        raise CommandError(f"There is no user with the username {username}.") from e


def get_user_profile(description: str, account: Optional[Account] = None, **lookup) -> UserProfile:
    """
    Return the one user profile that matches ``lookup``, in ``account`` if one is given.

    :param description: how the user was identified, for the error message, e.g. ``username jdoe``.
    :param account: the account to look in. Default: any account.
    :param lookup: the ``UserProfile`` query, e.g. ``user__email="jdoe@example.com"``.
    :returns: the user profile.
    :raises CommandError: if no user profile, or more than one, matches.
    """
    if account is not None:
        lookup["account"] = account
    try:
        return UserProfile.objects.get(**lookup)
    except UserProfile.DoesNotExist as e:
        where = f" in account {account.account_number}" if account is not None else ""
        raise CommandError(f"There is no user with the {description}{where}.") from e
    except UserProfile.MultipleObjectsReturned as e:
        raise CommandError(
            f"The user with the {description} belongs to several accounts. "
            "Add --account_number or --company_name to choose one."
        ) from e
