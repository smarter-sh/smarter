# pylint: disable=unused-argument
"""Django signal receivers for account app."""

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text

from .manifest.transformers.secret import SecretTransformer
from .models import Account, Charge, DailyBillingRecord, Secret, UserProfile
from .signals import (
    secret_created,
    secret_deleted,
    secret_edited,
    secret_inializing,
    secret_ready,
)
from .utils import (
    get_cached_account,
    get_cached_account_for_user,
    get_cached_default_account,
    get_cached_user_profile,
)


User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def user_logged_in_receiver(sender, request, user, **kwargs):
    """
    Signal receiver for user login.
    - verify that a UserProfile record exists for the user.
      if not, create one with the default account.
    """
    logger.info("%s User logged in signal received. user: %s", formatted_text("user_logged_in_receiver()"), user)
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
            formatted_text("user_post_save()"),
            instance,
            created,
        )


@receiver(post_delete, sender=User)
def user_post_delete(sender, instance, **kwargs):
    """Signal receiver for deleted of User model."""
    logger.info(
        "%s User post_delete signal received. instance: %s, id: %s",
        formatted_text("user_post_delete()"),
        instance,
        instance.id,
    )


@receiver(post_save, sender=UserProfile)
def user_profile_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of UserProfile model."""
    if created:
        logger.info(
            "%s UserProfile post_save signal received. instance: %s, created: %s",
            formatted_text("user_profile_post_save()"),
            instance,
            created,
        )


@receiver(post_delete, sender=UserProfile)
def user_profile_post_delete(sender, instance, **kwargs):
    """Signal receiver for deleted of UserProfile model."""
    get_cached_account_for_user.invalidate_cache(instance.user)
    get_cached_user_profile.invalidate_cache(instance.user, instance.account)
    logger.info(
        "%s UserProfile post_delete signal received. instance: %s, id: %s",
        formatted_text("user_profile_post_delete()"),
        instance,
        instance.id,
    )


@receiver(post_save, sender=Account)
def account_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of Account model."""
    if created:
        logger.info(
            "%s Account post_save signal received. instance: %s, created: %s",
            formatted_text("account_post_save()"),
            instance,
            created,
        )


@receiver(post_delete, sender=Account)
def account_post_delete(sender, instance, **kwargs):
    """Signal receiver for deleted of Account model."""
    get_cached_account.invalidate_cache(instance.id)
    logger.info(
        "%s Account post_delete signal received. instance: %s, id: %s",
        formatted_text("account_post_delete()"),
        instance,
        instance.id,
    )


@receiver(post_save, sender=Charge)
def charge_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of Charge model."""
    if created:
        logger.info(
            "%s Charge post_save signal received. instance: %s, created: %s",
            formatted_text("charge_post_save()"),
            instance,
            created,
        )


@receiver(post_save, sender=DailyBillingRecord)
def daily_billing_record_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of DailyBillingRecord model."""
    if created:
        logger.info(
            "%s DailyBillingRecord post_save signal received. instance: %s, created: %s",
            formatted_text("daily_billing_record_post_save()"),
            instance,
            created,
        )


@receiver(post_save, sender=Secret)
def secret_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of Secret model."""
    if created:
        logger.info(
            "%s Secret post_save signal received. instance: %s, id: %s created: %s",
            formatted_text("secret_post_save()"),
            instance,
            instance.id,
            created,
        )
        secret_created.send(sender=Secret, secret=instance)
    else:
        logger.info(
            "%s Secret post_save signal received. instance: %s, id: %s created: %s",
            formatted_text("secret_post_save()"),
            instance,
            instance.id,
            created,
        )
        secret_edited.send(sender=Secret, secret=instance)


@receiver(post_delete, sender=Secret)
def secret_post_delete(sender, instance, **kwargs):
    """Signal receiver for deleted of Secret model."""
    logger.info(
        "%s Secret post_delete signal received. instance: %s, id: %s",
        formatted_text("secret_post_delete()"),
        instance,
        instance.id,
    )


@receiver(secret_created)
def secret_created_receiver(sender, secret, **kwargs):
    """Signal receiver for secret_created signal."""
    logger.info(
        "%s.%s secret_created signal received. instance: %s id: %s",
        formatted_text("secret_created_receiver()"),
        sender,
        secret,
        secret.id,
    )


@receiver(secret_edited)
def secret_edited_receiver(sender, secret, **kwargs):
    """Signal receiver for secret_edited signal."""
    logger.info(
        "%s.%s secret_edited signal received. instance: %s, id: %s",
        formatted_text("secret_edited_receiver()"),
        sender,
        secret,
        secret.id,
    )


@receiver(secret_deleted)
def secret_deleted_receiver(sender, secret_id, secret_name, **kwargs):
    """Signal receiver for secret_deleted signal."""
    logger.info(
        "%s.%s secret_deleted signal received. instance: %s, name: %s",
        formatted_text("secret_deleted_receiver()"),
        sender,
        secret_id,
        secret_name,
    )


@receiver(secret_ready)
def secret_ready_receiver(sender, secret: SecretTransformer, **kwargs):
    """Signal receiver for secret_ready signal."""
    logger.info(
        "%s.%s secret_ready signal received. instance: %s, id: %s",
        formatted_text("secret_ready_receiver()"),
        sender,
        secret,
        secret.id,
    )


@receiver(secret_inializing)
def secret_inializing_receiver(sender, secret_name: str, user_profile: UserProfile, **kwargs):
    """Signal receiver for secret_inializing signal."""
    logger.info(
        "%s.%s secret_inializing signal received. name: %s, user_profile: %s",
        formatted_text("secret_inializing_receiver()"),
        sender,
        secret_name,
        user_profile,
    )
