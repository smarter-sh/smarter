# pylint: disable=unused-argument
"""Django signal receivers for secret app."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from smarter.apps.account.models import UserProfile
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import json, logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.typing import SmarterDictType

from .manifest.transformers.secret import SecretTransformer
from .models import Secret
from .signals import (
    secret_accessed,
    secret_created,
    secret_deleted,
    secret_inializing,
    secret_ready,
    secret_saved,
    secret_updated,
)


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


module_prefix = f"{__name__}"


def secret_log_dict(secret: Secret) -> SmarterDictType:
    """
    Return a Secret's fields for a log message, without its encrypted value.

    The ciphertext is as sensitive as the value: anyone with the logs and the platform's
    encryption key can decrypt it.

    :param secret: The Secret.
    :returns: The Secret's fields, except ``encrypted_value``.
    """
    return model_to_dict(secret, exclude=["encrypted_value"])


@receiver(post_save, sender=Secret)
def secret_post_save(sender: Secret, instance: Secret, created, **kwargs):
    """Signal receiver for created/saved of Secret model."""
    secret_json = json.dumps(secret_log_dict(instance))
    logger.debug(
        "%s Secret: %s, id: %s created: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.secret_post_save()"),
        secret_json,
        instance.id,  # type: ignore
        created,
        instance.user_profile,
    )


@receiver(post_delete, sender=Secret)
def secret_post_delete(sender: Secret, instance: Secret, **kwargs):
    """Signal receiver for deleted of Secret model."""
    logger.info(
        "%s Secret: %s, id: %s",
        formatted_text(f"{module_prefix}.secret_post_delete()"),
        instance,
        instance.id,  # type: ignore
    )


@receiver(secret_created)
def secret_created_receiver(sender, secret: Secret, **kwargs):
    """Signal receiver for secret_created signal."""
    logger.info(
        "%s.%s Secret: %s id: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.secret_created()"),
        type(sender),
        str(secret),
        secret.id,  # type: ignore
        secret.user_profile,
    )


@receiver(secret_deleted)
def secret_deleted_receiver(sender, secret_id, secret_name, **kwargs):
    """Signal receiver for secret_deleted signal."""
    logger.info(
        "%s.%s Secret: %s, name: %s",
        formatted_text(f"{module_prefix}.secret_deleted()"),
        type(sender),
        secret_id,
        secret_name,
    )


@receiver(secret_ready)
def secret_ready_receiver(sender, secret: SecretTransformer, **kwargs):
    """Signal receiver for secret_ready signal."""
    logger.info(
        "%s.%s Secret: %s, id: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.secret_ready()"),
        type(sender),
        str(secret),
        secret.id,
        secret.user_profile,
    )


@receiver(secret_accessed)
def secret_accessed_receiver(sender, secret: Secret, user_profile: UserProfile, **kwargs):
    """Signal receiver for secret_accessed signal."""
    logger.info(
        "%s.%s Secret: %s, id: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.secret_accessed()"),
        type(sender),
        str(secret),
        secret.id,  # type: ignore
        user_profile,
    )


@receiver(secret_inializing)
def secret_inializing_receiver(sender, secret_name: str, user_profile: UserProfile, **kwargs):
    """Signal receiver for secret_inializing signal."""
    logger.info(
        "%s.%s name: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.secret_inializing()"),
        type(sender),
        secret_name,
        user_profile,
    )


@receiver(secret_saved)
def secret_saved_receiver(sender, secret: SecretTransformer, user_profile: UserProfile, **kwargs):
    """Signal receiver for secret_saved signal."""
    if not secret.secret:
        raise ValueError("secret.secret is None in secret_saved_receiver")

    json_data = json.dumps(secret_log_dict(secret.secret))
    tags = list(secret.secret.tags_list) if secret and hasattr(secret.secret, "tags") else []

    logger.info(
        "%s.%s Secret: %s, id: %s, user_profile: %s, dump: %s, tags: %s",
        formatted_text(f"{module_prefix}.secret_saved()"),
        type(sender),
        str(secret),
        secret.id,
        user_profile,
        json_data,
        tags,
    )


@receiver(secret_updated)
def secret_updated_receiver(sender, secret: SecretTransformer, user_profile: UserProfile, **kwargs):
    """Signal receiver for secret_updated signal."""
    if not secret.secret:
        raise ValueError("secret.secret is None in secret_updated_receiver")

    json_data = json.dumps(secret_log_dict(secret.secret))
    tags = list(secret.secret.tags_list) if secret and hasattr(secret.secret, "tags") else []

    logger.info(
        "%s.%s secret_updated signal received. instance: %s, id: %s, user_profile: %s, dump: %s, tags: %s",
        formatted_text(f"{module_prefix}.secret_updated()"),
        type(sender),
        str(secret),
        secret.id,
        user_profile,
        json_data,
        tags,
    )
