"""Dict factories for testing views."""

import logging

from smarter.apps.account.models import (
    Secret,
)
from smarter.common.helpers.console_helpers import formatted_text
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
