# pylint: disable=unused-argument
"""Django signal receivers for account app."""

import logging

from django.contrib.auth.signals import user_logged_in
from django.core import serializers
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from smarter.common.conf import settings as smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import AbstractBroker

from .manifest.transformers.secret import SecretTransformer
from .models import Account, Charge, DailyBillingRecord, Secret, User, UserProfile
from .signals import (
    broker_ready,
    secret_accessed,
    secret_created,
    secret_deleted,
    secret_inializing,
    secret_ready,
    secret_saved,
    secret_updated,
)
from .utils import cache_invalidate, get_cached_default_account, get_cached_user_profile


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


module_prefix = "smarter.apps.account.receivers"


@receiver(user_logged_in)
def user_logged_in_receiver(sender, request, user: User, **kwargs):
    """
    Signal receiver for user login.
    - verify that a UserProfile record exists for the user.
      if not, create one with the default account.
    """
    logger.info("%s User logged in: %s", formatted_text(f"{module_prefix}.user_logged_in()"), user)
    if not get_cached_user_profile(user=user):
        logger.warning("User profile not found for user: %s", user)
        account = get_cached_default_account()
        UserProfile.objects.create(name=user.username, user=user, account=account)
        logger.info("Created UserProfile for user: %s with default account: %s", user, account)


@receiver(post_save, sender=User)
def user_post_save(sender: User, instance: User, created, **kwargs):
    """Signal receiver for created/saved of User model."""
    logger.info(
        "%s User post_save: %s, created: %s",
        formatted_text(f"{module_prefix}.user_post_save()"),
        instance,
        created,
    )
    if not created:
        cache_invalidate(user=instance)


@receiver(post_delete, sender=User)
def user_post_delete(sender: User, instance: User, **kwargs):
    """Signal receiver for deleted of User model."""
    logger.info(
        "%s User post_delete: %s, id: %s",
        formatted_text(f"{module_prefix}.user_post_delete()"),
        instance,
        instance.id,
    )


@receiver(post_save, sender=UserProfile)
def user_profile_post_save(sender: UserProfile, instance: UserProfile, created, **kwargs):
    """Signal receiver for created/saved of UserProfile model."""
    logger.info(
        "%s UserProfile post_save: %s, created: %s",
        formatted_text(f"{module_prefix}.user_profile_post_save()"),
        instance,
        created,
    )
    if not created:
        cache_invalidate(user=instance.user, account=instance.account)


@receiver(post_delete, sender=UserProfile)
def user_profile_post_delete(sender: UserProfile, instance: UserProfile, **kwargs):
    """Signal receiver for deleted of UserProfile model."""
    logger.info(
        "%s UserProfile: %s, id: %s",
        formatted_text(f"{module_prefix}.user_profile_post_delete()"),
        instance,
        instance.id,
    )


@receiver(post_save, sender=Account)
def account_post_save(sender: Account, instance: Account, created, **kwargs):
    """Signal receiver for created/saved of Account model."""
    model_prefix = formatted_text(f"{module_prefix}.account_post_save()")
    account_json = json.dumps(model_to_dict(instance))
    if created:
        logger.info("%s Account created: %s", model_prefix, instance)
    else:
        cache_invalidate(account=instance)

    logger.info("%s instance: %s", model_prefix, account_json)


@receiver(post_delete, sender=Account)
def account_post_delete(sender: Account, instance: Account, **kwargs):
    """Signal receiver for deleted of Account model."""
    logger.info(
        "%s Account post_delete: %s, id: %s",
        formatted_text(f"{module_prefix}.account_post_delete()"),
        instance,
        instance.id,
    )


@receiver(post_save, sender=Charge)
def charge_post_save(sender: Charge, instance: Charge, created, **kwargs):
    """Signal receiver for created/saved of Charge model."""
    charge_json = json.dumps(model_to_dict(instance))
    logger.info(
        "%s Charge post_save: %s, created: %s",
        formatted_text(f"{module_prefix}.charge_post_save()"),
        charge_json,
        created,
    )


@receiver(post_save, sender=DailyBillingRecord)
def daily_billing_record_post_save(sender: DailyBillingRecord, instance: DailyBillingRecord, created, **kwargs):
    """Signal receiver for created/saved of DailyBillingRecord model."""
    daily_billing_record_json = json.dumps(model_to_dict(instance))
    logger.info(
        "%s DailyBillingRecord: %s, created: %s",
        formatted_text(f"{module_prefix}.daily_billing_record_post_save()"),
        daily_billing_record_json,
        created,
    )


@receiver(post_save, sender=Secret)
def secret_post_save(sender: Secret, instance: Secret, created, **kwargs):
    """Signal receiver for created/saved of Secret model."""
    secret_json = json.dumps(model_to_dict(instance))
    logger.info(
        "%s Secret: %s, id: %s created: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.secret_post_save()"),
        secret_json,
        instance.id,
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
        instance.id,
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

    json_data = serializers.serialize("json", [secret.secret])
    tags = list(secret.secret.tags.names()) if secret and hasattr(secret.secret, "tags") else []

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

    json_data = serializers.serialize("json", [secret.secret])
    tags = list(secret.secret.tags.names()) if secret and hasattr(secret.secret, "tags") else []

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


@receiver(broker_ready)
def broker_ready_receiver(sender, broker: AbstractBroker, **kwargs):
    """Signal receiver for broker_ready signal."""
    logger.info(
        "%s %s %s for %s is ready.",
        formatted_text(f"{module_prefix}.broker_ready()"),
        broker.kind,
        str(broker),
        broker.name,
    )
