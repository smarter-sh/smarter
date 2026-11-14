"""
Delete the accounts, users and profiles that tests leave behind.

Smarter's tests run against the dev database, without a transaction to roll back, because many of them call
the live dev server. Each test class deletes what it creates, but a run that is interrupted, or a
``setUpClass()`` that fails (unittest then skips ``tearDownClass()``), leaves its rows behind.
:class:`smarter.lib.unittest.runner.SmarterTestRunner` calls :func:`purge_test_artifacts` before and after every
run, so that whatever happens, a run ends with none of them.

Test rows are found by the marks that :mod:`smarter.apps.account.tests.factories` gives them, not through their
relations: deleting a user deletes its profile but not its account, and deleting an account deletes its profiles
but not their users, so a row that has lost its profile can't be found through one.

- a ``UserProfile`` with ``is_test=True``;
- an ``Account`` whose name starts with one of :data:`TEST_ACCOUNT_NAME_PREFIXES`;
- a ``User`` whose username starts with one of :data:`TEST_USERNAME_PREFIXES`;
- a ``User`` named ``<account number>-admin`` (:data:`ACCOUNT_ADMIN_USERNAME_PATTERN`), without a profile, whose
  account no longer exists: a superuser that ``get_cached_admin_user_for_account()`` created for a test's account.

The Smarter account is never deleted, nor an account or user that still has a profile that is not a test's.
"""

import re
from dataclasses import dataclass, field

from smarter.apps.account.models import Account, AccountContact, User, UserProfile
from smarter.apps.account.utils import ACCOUNT_ADMIN_USERNAME_SUFFIX
from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

ADMIN_ACCOUNT_NAME_PREFIX = "test_account_admin_user_"
"""The name of each account that ``admin_user_factory()`` creates starts with this."""
MORTAL_ACCOUNT_NAME_PREFIX = "test_account_mortal_user_"
"""The name of each account that ``mortal_user_factory()`` creates starts with this."""
TEST_ACCOUNT_NAME_PREFIXES = (ADMIN_ACCOUNT_NAME_PREFIX, MORTAL_ACCOUNT_NAME_PREFIX)
"""The names of the accounts that the factories create start with one of these."""

ADMIN_USERNAME_PREFIX = "test_admin_user_"
"""The username of each user that ``admin_user_factory()`` creates starts with this."""
MORTAL_USERNAME_PREFIX = "test_mortal_user_"
"""The username of each user that ``mortal_user_factory()`` creates starts with this."""
TEST_USERNAME_PREFIXES = (ADMIN_USERNAME_PREFIX, MORTAL_USERNAME_PREFIX)
"""The usernames of the users that the factories create start with one of these."""

ACCOUNT_ADMIN_USERNAME_PATTERN = re.compile(r"^(\d{4}-\d{4}-\d{4})" + re.escape(ACCOUNT_ADMIN_USERNAME_SUFFIX) + "$")
"""The username of an admin user that ``get_cached_admin_user_for_account()`` created: its account number, then ``-admin``."""


@dataclass
class PurgeReport:
    """What :func:`purge_test_artifacts` deleted, and what it could not."""

    profiles: int = 0
    accounts: int = 0
    users: int = 0
    contacts: int = 0
    failures: list[str] = field(default_factory=list)

    @property
    def deleted(self) -> int:
        """The number of rows deleted."""
        return self.profiles + self.accounts + self.users + self.contacts


def accounts_with_other_members(account_ids: list[int]) -> set[int]:
    """
    The accounts, of those given, that still have a profile that is not a test's.

    :param account_ids: The accounts' ids.
    :returns: The ids of those that a real user belongs to, which are never deleted.
    """
    profiles = UserProfile.objects.filter(account_id__in=account_ids, is_test=False)
    retval = set(profiles.values_list("account_id", flat=True))
    return retval


def orphaned_account_admin_ids() -> set[int]:
    """
    The admin users that ``get_cached_admin_user_for_account()`` created for accounts that no longer exist.

    Such a user is named ``<account number>-admin``, and is a superuser. Deleting its account now deletes it too,
    but one left by an older run, or by a deletion that bypassed ``Account.delete()``, stays without a profile.

    :returns: The ids of those users.
    """
    retval: set[int] = set()
    candidates = User.objects.filter(username__endswith=ACCOUNT_ADMIN_USERNAME_SUFFIX)
    for user in candidates:
        match = ACCOUNT_ADMIN_USERNAME_PATTERN.match(user.username)
        if match is None:
            continue
        if UserProfile.objects.filter(user=user).exists():
            continue
        account_number = match.group(1)
        if Account.objects.filter(account_number=account_number).exists():
            continue
        retval.add(user.pk)
    return retval


def delete_test_accounts(account_ids: set[int], report: PurgeReport) -> None:
    """
    Delete the test accounts, except the Smarter account and any that a real user belongs to.

    :param account_ids: The ids of the test accounts.
    :param report: Counts the deleted accounts, and records each one that could not be deleted.
    """
    accounts = Account.objects.filter(pk__in=account_ids).exclude(account_number=SMARTER_ACCOUNT_NUMBER)
    kept = accounts_with_other_members(list(accounts.values_list("pk", flat=True)))
    accounts = accounts.exclude(pk__in=kept)
    # an account with children is protected, and the accounts are in no particular order.
    accounts.update(parent=None)
    for account in accounts:
        try:
            AccountContact.objects.filter(account=account).delete()
            account.delete()
            report.accounts += 1
        # pylint: disable=broad-except
        except Exception as e:
            # the exception's type only: its message may name the account's users.
            report.failures.append(f"Account id {account.pk}: {type(e).__name__}")


def delete_test_users(user_ids: set[int], report: PurgeReport) -> None:
    """
    Delete the test users, except any that still has a profile.

    :param user_ids: The ids of the test users.
    :param report: Counts the deleted users, and records each one that could not be deleted.
    """
    profiles = UserProfile.objects.filter(user_id__in=user_ids)
    users_with_profiles = set(profiles.values_list("user_id", flat=True))
    users = User.objects.filter(pk__in=user_ids).exclude(pk__in=users_with_profiles)
    for user in users:
        try:
            user.delete()
            report.users += 1
        # pylint: disable=broad-except
        except Exception as e:
            # the exception's type only: its message may name the user.
            report.failures.append(f"User id {user.pk}: {type(e).__name__}")


def purge_test_artifacts() -> PurgeReport:
    """
    Delete every test profile, and the factories' accounts and users, wherever a test left them.

    Each row is deleted on its own, so that one that can't be deleted doesn't keep the others. A failure is
    logged and reported, not raised: a cleanup must not fail the test run.

    :returns: What was deleted, and what could not be.
    """
    report = PurgeReport()

    test_profiles = UserProfile.objects.filter(is_test=True)
    account_ids = set(test_profiles.values_list("account_id", flat=True))
    user_ids = set(test_profiles.values_list("user_id", flat=True))
    report.profiles = test_profiles.count()
    test_profiles.delete()

    for prefix in TEST_ACCOUNT_NAME_PREFIXES:
        named_accounts = Account.objects.filter(name__startswith=prefix).values_list("pk", flat=True)
        account_ids.update(named_accounts)
    for prefix in TEST_USERNAME_PREFIXES:
        named_users = User.objects.filter(username__startswith=prefix).values_list("pk", flat=True)
        user_ids.update(named_users)
    user_ids.update(orphaned_account_admin_ids())

    delete_test_accounts(account_ids, report)
    delete_test_users(user_ids, report)

    test_contacts = AccountContact.objects.filter(is_test=True)
    report.contacts = test_contacts.count()
    test_contacts.delete()

    if report.deleted:
        logger.warning(
            "%s.purge_test_artifacts() deleted %s test profiles, %s accounts, %s users and %s contacts that tests left behind.",
            logger_prefix,
            report.profiles,
            report.accounts,
            report.users,
            report.contacts,
        )
    for failure in report.failures:
        logger.error("%s.purge_test_artifacts() could not delete %s", logger_prefix, failure)
    return report


__all__ = [
    "ACCOUNT_ADMIN_USERNAME_PATTERN",
    "ADMIN_ACCOUNT_NAME_PREFIX",
    "ADMIN_USERNAME_PREFIX",
    "MORTAL_ACCOUNT_NAME_PREFIX",
    "MORTAL_USERNAME_PREFIX",
    "PurgeReport",
    "TEST_ACCOUNT_NAME_PREFIXES",
    "TEST_USERNAME_PREFIXES",
    "accounts_with_other_members",
    "delete_test_accounts",
    "delete_test_users",
    "orphaned_account_admin_ids",
    "purge_test_artifacts",
]
