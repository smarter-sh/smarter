"""Dict factories for testing views."""

import uuid
from typing import Optional

from smarter.apps.account.models import (
    Account,
    AccountContact,
    User,
    UserProfile,
)
from smarter.apps.account.tests.cleanup import (
    ADMIN_ACCOUNT_NAME_PREFIX,
    ADMIN_USERNAME_PREFIX,
    MORTAL_ACCOUNT_NAME_PREFIX,
    MORTAL_USERNAME_PREFIX,
    purge_test_artifacts,
)
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.utils import hash_factory, to_snake_case
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

HERE = SmarterFormattedText.text(__name__)
COMMON_VERSION = "0.0.1"

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING])


def admin_user_factory(account: Optional[Account] = None) -> tuple[User, Account, UserProfile]:
    hashed_slug = hash_factory()
    username = to_snake_case(f"{ADMIN_USERNAME_PREFIX}{hashed_slug}")
    email = f"test-admin-{hashed_slug}@mail.com"
    first_name = f"TestAdminFirstName_{hashed_slug}"
    last_name = f"TestAdminLastName_{hashed_slug}"

    # annotations is a MetaDataModel property, not a field, which Model.__init__() accepts but mypy does not.
    account = account or Account.objects.create(  # type: ignore[misc]
        name=f"{ADMIN_ACCOUNT_NAME_PREFIX}{hashed_slug}",
        description="Account for admin user testing purposes",
        version=COMMON_VERSION,
        is_default_account=False,
        is_active=True,
        company_name=f"TestAccount_AdminUser_{hashed_slug}",
        phone_number="123-456-789",
        address1="Smarter Way 4U",
        address2="Suite 100",
        city="Smarter",
        state="WY",
        postal_code="12345",
        country="USA",
        language="EN",
        timezone="America/New_York",
        currency="USD",
        annotations=[
            {"smarter.sh/created_by": "admin_user_factory"},
            {"smarter.sh/purpose": "testing"},
            {"smarter.sh/hash": hashed_slug},
        ],
    )
    account.tags.set(["test", "admin", "account"])

    user = User.objects.create_user(
        email=email,
        first_name=first_name,
        last_name=last_name,
        username=username,  # type: ignore[arg-type]
        password="12345",
        is_active=True,
        is_staff=True,
        is_superuser=True,
    )

    user_profile = UserProfile.objects.create(
        name=user.username,
        description="Admin user profile for testing purposes",
        version=COMMON_VERSION,
        user=user,
        account=account,
        is_test=True,
        annotations=[{"smarter.sh/role": "admin"}, {"smarter.sh/environment": "test"}],
    )
    user_profile.tags.set(["admin", "test"])

    return user, account, user_profile


def platform_staff_profile_factory(user: User) -> UserProfile:
    """
    Give a user a profile in the Smarter account, which makes a staff user one of the platform's staff.

    See :func:`smarter.apps.account.utils.is_platform_staff`. The test deletes the profile when it is
    done, e.g. in ``tearDownClass``. Deleting the user deletes it too.

    The profile is not ``is_test``: :func:`factory_account_teardown` deletes every ``is_test``
    profile's account, and this one's is the Smarter account.

    :param user: The user, usually from :func:`admin_user_factory`, which is staff.
    :returns: The user's new profile in the Smarter account.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.account.utils import smarter_cached_objects

    user_profile = UserProfile.objects.create(
        name=user.username,
        description="Platform staff user profile for testing purposes",
        version=COMMON_VERSION,
        user=user,
        account=smarter_cached_objects.smarter_account,
        is_test=False,
    )
    return user_profile


def mortal_user_factory(account: Optional[Account] = None) -> tuple[User, Account, UserProfile]:
    hashed_slug = hash_factory()
    username = str(to_snake_case(f"{MORTAL_USERNAME_PREFIX}{hashed_slug}"))
    email = f"test-mortal-{hashed_slug}@mail.com"
    first_name = f"TestMortalFirstName_{hashed_slug}"
    last_name = f"TestMortalLastName_{hashed_slug}"

    # annotations is a MetaDataModel property, not a field, which Model.__init__() accepts but mypy does not.
    account = account or Account.objects.create(  # type: ignore[misc]
        name=f"{MORTAL_ACCOUNT_NAME_PREFIX}{hashed_slug}",
        description="Account for mortal user testing purposes",
        version=COMMON_VERSION,
        is_default_account=False,
        is_active=True,
        company_name=f"TestAccount_MortalUser_{hashed_slug}",
        phone_number="123-456-789",
        address1="Smarter Way 4U",
        address2="Suite 100",
        city="Smarter",
        state="WY",
        postal_code="12345",
        country="USA",
        language="EN",
        timezone="America/New_York",
        currency="USD",
        annotations=[
            {"smarter.sh/created_by": "mortal_user_factory"},
            {"smarter.sh/purpose": "testing"},
            {"smarter.sh/hash": hashed_slug},
        ],
    )
    account.tags.set(["test", "mortal", "account"])

    user = User.objects.create_user(
        email=email,
        first_name=first_name,
        last_name=last_name,
        username=username,
        password="12345",
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )

    user_profile = UserProfile.objects.create(
        name=user.username,
        description="Mortal user profile for testing purposes",
        version=COMMON_VERSION,
        user=user,
        account=account,
        is_test=True,
        annotations=[{"smarter.sh/role": "mortal"}, {"smarter.sh/environment": "test"}],
    )
    user_profile.tags.set(["mortal", "test"])

    return user, account, user_profile


def factory_account_teardown(user: User, account: Optional[Account], user_profile: Optional[UserProfile]):
    if user and account and not user_profile:
        user_profile = UserProfile.get_cached_object(user=user, account=account)
    elif user and not user_profile:
        user_profile = UserProfile.objects.filter(user=user).first()

    try:
        if user_profile:
            AccountContact.objects.filter(email=user_profile.user.email, account=user_profile.account).delete()
    except AccountContact.DoesNotExist:
        pass
    try:
        if user_profile:
            lbl = str(user_profile)
            user_profile.delete()
            logger.debug("%s.factory_account_teardown() Deleted user profile for %s", HERE, lbl)

    except UserProfile.DoesNotExist:
        pass
    try:
        if user:
            lbl = str(user)
            user.delete()
            logger.debug("%s.factory_account_teardown() Deleted user: %s", HERE, lbl)
    except User.DoesNotExist:
        pass
    try:
        if account:
            lbl = str(account)
            account.delete()
            logger.debug("%s.factory_account_teardown() Deleted account: %s", HERE, lbl)
    except Account.DoesNotExist:
        pass

    # whatever else tests created and failed to delete, found by the factories' marks rather than through
    # relations that an earlier, partial cleanup may have broken.
    purge_test_artifacts()


def billing_address_factory():
    """Factory for testing billing addresses."""

    return {
        "id": str(uuid.uuid4()),
        "is_primary": True,
        "address1": "123 Main St",
        "address2": "Apt 123",
        "city": "Anytown",
        "state": "CA",
        "zip": "12345",
        "country": "US",
    }
