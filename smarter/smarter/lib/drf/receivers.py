# pylint: disable=unused-argument
"""Django signal receivers for account app."""

import logging

from django.core import serializers
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from rest_framework.exceptions import AuthenticationFailed

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
    return waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
module_prefix = "smarter.lib.drf.receivers"


@receiver(post_save, sender=SmarterAuthToken)
def handle_auth_token_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of SmarterAuthToken model."""
    json_data = serializers.serialize("json", [instance])
    if created:
        logger.debug(
            "%s SmarterAuthToken: %s, created: %s",
            formatted_text(f"{module_prefix}.smarter_auth_token_save()"),
            json_data,
            created,
        )
    else:
        logger.debug(
            "%s SmarterAuthToken: %s, created: %s",
            formatted_text(f"{module_prefix}.smarter_auth_token_save()"),
            json_data,
            created,
        )


@receiver(post_delete, sender=SmarterAuthToken)
def handle_smarter_auth_token_delete(sender, instance, **kwargs):
    """Signal receiver for deleted of SmarterAuthToken model."""
    logger.debug(
        "%s SmarterAuthToken: %s",
        formatted_text(f"{module_prefix}.smarter_auth_token_delete()"),
        instance,
    )


@receiver(smarter_token_authentication_request)
def handle_smarter_token_authentication_request(sender, token, url, **kwargs):
    """Signal receiver for authentication request."""
    logger.debug(
        "%s sender: %s, token: %s, url: %s",
        formatted_text(f"{module_prefix}.smarter_token_authentication_request()"),
        sender,
        token,
        url,
    )


@receiver(smarter_token_authentication_success)
def handle_smarter_token_authentication_success(sender, user, token, **kwargs):
    """Signal receiver for authorization granted."""
    logger.debug(
        "%s sender: %s, user: %s, token: %s",
        formatted_text(f"{module_prefix}.smarter_token_authentication_success()"),
        sender,
        user,
        token,
    )


@receiver(smarter_token_authentication_failure)
def handle_smarter_token_authentication_failure(sender, user, token, error: AuthenticationFailed, **kwargs):
    """Signal receiver for authorization denied."""
    logger.warning(
        "%s sender: %s, user: %s, token: %s, error: %s",
        formatted_text(f"{module_prefix}.smarter_token_authentication_failure()"),
        sender,
        user,
        token,
        str(error),
    )
