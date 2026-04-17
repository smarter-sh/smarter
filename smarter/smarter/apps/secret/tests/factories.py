"""Dict factories for testing views."""

import logging
from datetime import datetime
from typing import Optional

from smarter.apps.account.models import UserProfile
from smarter.apps.secret.models import Secret
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import camel_to_snake
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

HERE = formatted_text(__name__)


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


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
