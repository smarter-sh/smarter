# pylint: disable=unused-argument
"""Django signal receivers for account app."""

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .models import SmarterAuthToken
from .signals import (
    smarter_token_authentication_failure,
    smarter_token_authentication_request,
    smarter_token_authentication_success,
)


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
module_prefix = "smarter.lib.drf.receivers"


@receiver(post_save, sender=SmarterAuthToken)
def smarter_auth_token_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of SmarterAuthToken model."""
    if created:
        logger.info(
            "%s.%s SmarterAuthToken post_save signal received. instance: %s, created: %s",
            module_prefix,
            formatted_text("smarter_auth_token_save()"),
            instance,
            created,
        )
    else:
        logger.info(
            "%s.%s SmarterAuthToken post_save signal received. instance: %s, created: %s",
            module_prefix,
            formatted_text("smarter_auth_token_save()"),
            instance,
            created,
        )


@receiver(post_delete, sender=SmarterAuthToken)
def smarter_auth_token_delete(sender, instance, **kwargs):
    """Signal receiver for deleted of SmarterAuthToken model."""
    logger.info(
        "%s.%s SmarterAuthToken post_delete signal received. instance: %s",
        module_prefix,
        formatted_text("smarter_auth_token_delete()"),
        instance,
    )


@receiver(smarter_token_authentication_request)
def authentication_request_receiver(sender, token, **kwargs):
    """Signal receiver for authentication request."""
    logger.info(
        "%s signal received. sender: %s, token: %s",
        formatted_text(f"{module_prefix}.smarter_token_authentication_request()"),
        sender,
        token,
    )


@receiver(smarter_token_authentication_success)
def authorization_granted_receiver(sender, user, token, **kwargs):
    """Signal receiver for authorization granted."""
    logger.info(
        "%s signal received. sender: %s, user: %s, token: %s",
        formatted_text(f"{module_prefix}.smarter_token_authentication_success()"),
        sender,
        user,
        token,
    )


@receiver(smarter_token_authentication_failure)
def authorization_denied_receiver(sender, user, token, **kwargs):
    """Signal receiver for authorization denied."""
    logger.info(
        "%s signal received. sender: %s, user: %s, token: %s",
        formatted_text(f"{module_prefix}.smarter_token_authentication_failure()"),
        sender,
        user,
        token,
    )
