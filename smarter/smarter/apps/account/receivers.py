# pylint: disable=unused-argument
"""Django signal receivers for account app."""

import logging

from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .manifest.transformers.secret import SecretTransformer
from .models import Account, Charge, DailyBillingRecord, Secret, User, UserProfile
from .signals import (
    secret_accessed,
    secret_created,
    secret_deleted,
    secret_inializing,
    secret_ready,
)
from .utils import get_cached_default_account, get_cached_user_profile


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)
        and level >= logging.INFO
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


module_prefix = "smarter.apps.account.receivers"


@receiver(user_logged_in)
def user_logged_in_receiver(sender, request, user, **kwargs):
    """
    Signal receiver for user login.
    - verify that a UserProfile record exists for the user.
      if not, create one with the default account.
    """
    logger.info(
        "%s User logged in signal received. user: %s", formatted_text(f"{module_prefix}.user_logged_in()"), user
    )
    if not get_cached_user_profile(user=user):
        logger.warning("User profile not found for user: %s", user)
        account = get_cached_default_account()
        UserProfile.objects.create(user=user, account=account)


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of User model."""
    if created:
        logger.info(
            "%s User post_save signal received. instance: %s, created: %s",
            formatted_text(f"{module_prefix}.user_post_save()"),
            instance,
            created,
        )


@receiver(post_delete, sender=User)
def user_post_delete(sender, instance, **kwargs):
    """Signal receiver for deleted of User model."""
    logger.info(
        "%s User post_delete signal received. instance: %s, id: %s",
        formatted_text(f"{module_prefix}.user_post_delete()"),
        instance,
        instance.id,
    )


@receiver(post_save, sender=UserProfile)
def user_profile_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of UserProfile model."""
    if created:
        logger.info(
            "%s UserProfile post_save signal received. instance: %s, created: %s",
            formatted_text(f"{module_prefix}.user_profile_post_save()"),
            instance,
            created,
        )


@receiver(post_delete, sender=UserProfile)
def user_profile_post_delete(sender, instance, **kwargs):
    """Signal receiver for deleted of UserProfile model."""
    logger.info(
        "%s UserProfile post_delete signal received. instance: %s, id: %s",
        formatted_text(f"{module_prefix}.user_profile_post_delete()"),
        instance,
        instance.id,
    )


@receiver(post_save, sender=Account)
def account_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of Account model."""
    if created:
        logger.info(
            "%s Account post_save signal received. instance: %s, created: %s",
            formatted_text(f"{module_prefix}.account_post_save()"),
            instance,
            created,
        )


@receiver(post_delete, sender=Account)
def account_post_delete(sender, instance, **kwargs):
    """Signal receiver for deleted of Account model."""
    logger.info(
        "%s Account post_delete signal received. instance: %s, id: %s",
        formatted_text(f"{module_prefix}.account_post_delete()"),
        instance,
        instance.id,
    )


@receiver(post_save, sender=Charge)
def charge_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of Charge model."""
    if created:
        logger.info(
            "%s Charge post_save signal received. instance: %s, created: %s",
            formatted_text(f"{module_prefix}.charge_post_save()"),
            instance,
            created,
        )


@receiver(post_save, sender=DailyBillingRecord)
def daily_billing_record_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of DailyBillingRecord model."""
    if created:
        logger.info(
            "%s DailyBillingRecord post_save signal received. instance: %s, created: %s",
            formatted_text(f"{module_prefix}.daily_billing_record_post_save()"),
            instance,
            created,
        )


@receiver(post_save, sender=Secret)
def secret_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of Secret model."""
    if created:
        logger.info(
            "%s Secret post_save signal received. instance: %s, id: %s created: %s",
            formatted_text(f"{module_prefix}.secret_post_save()"),
            instance,
            instance.id,
            created,
        )


@receiver(post_delete, sender=Secret)
def secret_post_delete(sender, instance, **kwargs):
    """Signal receiver for deleted of Secret model."""
    logger.info(
        "%s Secret post_delete signal received. instance: %s, id: %s",
        formatted_text(f"{module_prefix}.secret_post_delete()"),
        instance,
        instance.id,
    )


@receiver(secret_created)
def secret_created_receiver(sender, secret: Secret, **kwargs):
    """Signal receiver for secret_created signal."""
    logger.info(
        "%s.%s secret_created signal received. instance: %s id: %s",
        formatted_text(f"{module_prefix}.secret_created()"),
        sender,
        str(secret),
        secret.id,  # type: ignore
    )


@receiver(secret_deleted)
def secret_deleted_receiver(sender, secret_id, secret_name, **kwargs):
    """Signal receiver for secret_deleted signal."""
    logger.info(
        "%s.%s secret_deleted signal received. instance: %s, name: %s",
        formatted_text(f"{module_prefix}.secret_deleted()"),
        sender,
        secret_id,
        secret_name,
    )


@receiver(secret_ready)
def secret_ready_receiver(sender, secret: SecretTransformer, **kwargs):
    """Signal receiver for secret_ready signal."""
    logger.info(
        "%s.%s secret_ready signal received. instance: %s, id: %s",
        formatted_text(f"{module_prefix}.secret_ready()"),
        sender,
        str(secret),
        secret.id,
    )


@receiver(secret_accessed)
def secret_accessed_receiver(sender, secret: Secret, user_profile: UserProfile, **kwargs):
    """Signal receiver for secret_accessed signal."""
    logger.info(
        "%s.%s secret_accessed signal received. instance: %s, id: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.secret_accessed()"),
        sender,
        str(secret),
        secret.id,  # type: ignore
        user_profile,
    )


@receiver(secret_inializing)
def secret_inializing_receiver(sender, secret_name: str, user_profile: UserProfile, **kwargs):
    """Signal receiver for secret_inializing signal."""
    logger.info(
        "%s.%s secret_inializing signal received. name: %s, user_profile: %s",
        formatted_text(f"{module_prefix}.secret_inializing()"),
        sender,
        secret_name,
        user_profile,
    )
