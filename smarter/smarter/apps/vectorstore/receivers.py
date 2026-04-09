# pylint: disable=unused-argument
"""
Receivers for the vectorstore app.
"""

import json
import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from smarter.apps.vectorstore.models import VectorDatabase
from smarter.apps.vectorstore.signals import (
    embed_failed,
    embed_started,
    embed_success,
    load_failed,
    load_started,
    load_success,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=unused-argument
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.VECTORSTORE_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
module_prefix = f"{__name__}"


@receiver(post_save, sender=VectorDatabase)
def account_post_save(sender: VectorDatabase, instance: VectorDatabase, created, **kwargs):
    """Signal receiver for created/saved of VectorDatabase model."""
    model_prefix = formatted_text(f"{module_prefix}.account_post_save()")
    account_json = json.dumps(model_to_dict(instance))
    if created:
        logger.info("%s VectorDatabase created: %s", model_prefix, account_json)
    else:
        logger.info("%s VectorDatabase updated: %s", model_prefix, account_json)
        logger.info(
            "%s invalidating cache for VectorDatabase: %s",
            formatted_text(f"{module_prefix}.account_post_save()"),
            instance,
        )
        VectorDatabase.get_cached_object(invalidate=True, pk=instance.pk)


@receiver(post_delete, sender=VectorDatabase)
def account_post_delete(sender: VectorDatabase, instance: VectorDatabase, **kwargs):
    """Signal receiver for deleted of VectorDatabase model."""
    model_prefix = formatted_text(f"{module_prefix}.account_post_delete()")
    account_json = json.dumps(model_to_dict(instance))
    logger.info("%s VectorDatabase deleted: %s", model_prefix, account_json)
    logger.info(
        "%s invalidating cache for deleted VectorDatabase: %s",
        formatted_text(f"{module_prefix}.account_post_delete()"),
        instance,
    )
    VectorDatabase.get_cached_object(invalidate=True, pk=instance.pk)


@receiver(load_started)
def handle_load_started(sender, backend, provider, user_profile, **kwargs):
    """Signal receiver for load_started signal."""
    logger.info(
        "%s load started for backend: %s, provider: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.handle_load_started()"),
        backend,
        provider,
        user_profile,
    )


@receiver(load_success)
def handle_load_success(sender, backend, provider, user_profile, **kwargs):
    """Signal receiver for load_success signal."""
    logger.info(
        "%s load succeeded for backend: %s, provider: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.handle_load_success()"),
        backend,
        provider,
        user_profile,
    )


@receiver(load_failed)
def handle_load_failed(sender, backend, provider, user_profile, **kwargs):
    """Signal receiver for load_failed signal."""
    logger.error(
        "%s load failed for backend: %s, provider: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.handle_load_failed()"),
        backend,
        provider,
        user_profile,
    )


@receiver(embed_started)
def handle_embed_started(sender, backend, provider, user_profile, **kwargs):
    """Signal receiver for embed_started signal."""
    logger.info(
        "%s embed started for backend: %s, provider: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.handle_embed_started()"),
        backend,
        provider,
        user_profile,
    )


@receiver(embed_success)
def handle_embed_success(sender, backend, provider, user_profile, **kwargs):
    """Signal receiver for embed_success signal."""
    logger.info(
        "%s embed succeeded for backend: %s, provider: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.handle_embed_success()"),
        backend,
        provider,
        user_profile,
    )


@receiver(embed_failed)
def handle_embed_failed(sender, backend, provider, user_profile, **kwargs):
    """Signal receiver for embed_failed signal."""
    logger.error(
        "%s embed failed for backend: %s, provider: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.handle_embed_failed()"),
        backend,
        provider,
        user_profile,
    )
