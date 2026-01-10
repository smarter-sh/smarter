"""Dict factories for testing views."""

import logging
import random
import uuid
from datetime import datetime
from typing import Optional

from smarter.apps.account.models import (
    Account,
    PaymentMethod,
    Secret,
    User,
    UserProfile,
)
from smarter.apps.account.utils import get_cached_user_profile
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import camel_to_snake, hash_factory
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.unittest.base_classes import SmarterTestBase


HERE = formatted_text(__name__)
COMMON_VERSION = "0.0.1"


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


def admin_user_factory(account: Optional[Account] = None) -> tuple[User, Account, UserProfile]:
    hashed_slug = hash_factory()
    username = camel_to_snake(f"testAdminUser_{hashed_slug}")
    email = f"test-admin-{hashed_slug}@mail.com"
    first_name = f"TestAdminFirstName_{hashed_slug}"
    last_name = f"TestAdminLastName_{hashed_slug}"

    account = account or Account.objects.create(
        name=f"test_account_admin_user_{hashed_slug}",
        description="Account for admin user testing purposes",
        version=COMMON_VERSION,
        is_default_account=True,
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


def mortal_user_factory(account: Optional[Account] = None) -> tuple[User, Account, UserProfile]:
    hashed_slug = hash_factory()
    username = str(camel_to_snake(f"testAdminUser_{hashed_slug}"))
    email = f"test-mortal-{hashed_slug}@mail.com"
    first_name = f"TestMortalFirstName_{hashed_slug}"
    last_name = f"TestMortalLastName_{hashed_slug}"

    account = account or Account.objects.create(
        name=f"test_account_mortal_user_{hashed_slug}",
        description="Account for mortal user testing purposes",
        version=COMMON_VERSION,
        is_default_account=True,
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


def factory_account_teardown(user: User, account: Optional[Account], user_profile: UserProfile):
    if user and account and not user_profile:
        user_profile = get_cached_user_profile(user=user, account=account)
    elif user and not user_profile:
        user_profile = UserProfile.objects.filter(user=user).first()
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


def payment_method_factory(account: Account):
    """
    Factory for creating a PaymentMethod object for testing.
    """

    payment_method = PaymentMethod.objects.create(
        account=account,
        name=camel_to_snake("TestPaymentMethod" + SmarterTestBase.generate_hash_suffix()),
        stripe_id="test-stripe-id",
        card_type="test_card_type",
        card_last_4=random.randint(1000, 9999),
        card_exp_month=random.randint(1, 12),
        card_exp_year=random.randint(datetime.now().year, datetime.now().year + 7),
        is_default=True,
    )
    logger.debug("%s.payment_method_factory() Created payment method: %s", HERE, payment_method.name)
    return payment_method


def payment_method_factory_teardown(payment_method: PaymentMethod):
    try:
        if payment_method:
            lbl = str(payment_method)
            payment_method.delete()
            logger.debug("%s.payment_method_factory_teardown() Deleted payment method: %s", HERE, lbl)
    except PaymentMethod.DoesNotExist:
        pass
    except Exception as e:
        logger.error("%s.payment_method_factory_teardown() Error deleting payment method: %s", HERE, e)
        raise


def secret_factory(
    user_profile: UserProfile, name: str, description: str, value: str, expiration: Optional[datetime] = None
) -> Secret:
    """
    Create a Secret object for testing.

    Args:
        user_profile (UserProfile): The UserProfile associated with the secret.
        name (str): The name of the secret.
        description (str): A description of the secret.
        value (str): The value of the secret.

    Returns:
        Secret: The created Secret object.
    """
    encrypted_value = Secret.encrypt(value)
    secret = Secret.objects.create(
        user_profile=user_profile,
        name=camel_to_snake(name),
        description=description,
        encrypted_value=encrypted_value,
        expires_at=expiration,
    )
    logger.debug("%s.secret_factory() Created secret: %s", HERE, secret)
    return secret


def factory_secret_teardown(secret: Secret):
    try:
        if secret:
            lbl = str(secret)
            secret.delete()
            logger.debug("%s.factory_secret_teardown() Deleted secret: %s", HERE, lbl)
    except Secret.DoesNotExist:
        pass
    except Exception as e:
        logger.error("%s.factory_secret_teardown() Error deleting secret: %s", HERE, e)
        raise
