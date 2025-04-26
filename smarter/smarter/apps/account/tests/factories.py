"""Dict factories for testing views."""

import hashlib
import logging
import random
import uuid
from datetime import datetime

from smarter.apps.account.models import Account, UserProfile
from smarter.lib.django.user import User, UserType


logger = logging.getLogger(__name__)


def admin_user_factory(account: Account = None) -> tuple[UserType, Account, UserProfile]:
    hashed_slug = hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:16]
    username = f"testAdminUser_{hashed_slug}"
    user = User.objects.create_user(
        username=username, password="12345", is_active=True, is_staff=True, is_superuser=True
    )
    logger.info("admin_user_factory() Created admin user: %s", username)
    account = account or Account.objects.create(company_name=f"TestAccount_{hashed_slug}", phone_number="123-456-789")
    logger.info("admin_user_factory() Created account: %s", account.id)
    user_profile = UserProfile.objects.create(user=user, account=account, is_test=True)
    logger.info("admin_user_factory() Created user profile %s", user_profile)

    return user, account, user_profile


def mortal_user_factory(account: Account = None) -> tuple[UserType, Account, UserProfile]:
    hashed_slug = hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()[:16]
    username = f"testMortalUser_{hashed_slug}"
    user = User.objects.create_user(
        username=username, password="12345", is_active=True, is_staff=False, is_superuser=False
    )
    logger.info("mortal_user_factory() Created mortal user: %s", username)
    account = account or Account.objects.create(company_name=f"TestAccount_{hashed_slug}", phone_number="123-456-789")
    logger.info("mortal_user_factory() Created/set account: %s", account.id)
    user_profile = UserProfile.objects.create(user=user, account=account, is_test=True)
    logger.info("mortal_user_factory() Created user profile %s", user_profile)

    return user, account, user_profile


def admin_user_teardown(user: UserType, account: Account, user_profile: UserProfile):
    try:
        if user_profile:
            lbl = str(user_profile)
            user_profile.delete()
            logger.info("admin_user_teardown() Deleted user profile for %s", lbl)

    except UserProfile.DoesNotExist:
        pass
    try:
        if user:
            lbl = str(user)
            user.delete()
            logger.info("admin_user_teardown() Deleted user: %s", lbl)
    except User.DoesNotExist:
        pass
    try:
        if account:
            lbl = str(account)
            account.delete()
            logger.info("admin_user_teardown() Deleted account: %s", lbl)
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


def payment_method_factory():

    def generate_card_number(card_type: str = "visa"):
        if card_type == "visa":
            return "4" + "".join(random.choices("0123456789", k=15))
        if card_type == "mastercard":
            return "5" + "".join(random.choices("0123456789", k=15))
        if card_type == "american-express":
            return "3" + "".join(random.choices("0123456789", k=14))
        return "-".join(["".join(random.choices("0123456789", k=4)) for _ in range(4)])

    def mask_card(card_number):
        return "ending " + str(card_number)[-4:]

    card_type = random.choice(["visa", "mastercard", "american-express"])
    card_number = generate_card_number(card_type)
    card_masked = mask_card(card_number)
    return {
        "id": str(uuid.uuid4()),
        "is_primary": True,
        "card_type": card_type,
        "card_name": "John Doe",
        "card_number": card_number,
        "card_masked": card_masked,
        "card_expiration_month": 12,
        "card_expiration_year": random.randint(datetime.now().year, datetime.now().year + 7),
        "card_cvc": random.randint(100, 999),
    }
