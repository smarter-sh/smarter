# pylint: disable=unused-argument
"""Django signal receivers for account app."""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text

from .models import SmarterAuthToken


logger = logging.getLogger(__name__)


@receiver(post_save, sender=SmarterAuthToken)
def smarter_auth_token_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of SmarterAuthToken model."""
    if created:
        logger.info(
            "%s SmarterAuthToken post_save signal received. instance: %s, created: %s",
            formatted_text("smarter_auth_token_save()"),
            instance,
            created,
        )
    else:
        logger.info(
            "%s SmarterAuthToken post_save signal received. instance: %s, created: %s",
            formatted_text("smarter_auth_token_save()"),
            instance,
            created,
        )
