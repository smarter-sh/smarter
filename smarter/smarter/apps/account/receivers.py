# pylint: disable=unused-argument
"""Django signal receivers for account app."""

import logging

from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text

from .models import Account, Charge, DailyBillingRecord, Secret, UserProfile
from .signals import new_secret_created, secret_edited
from .utils import get_cached_default_account, get_cached_user_profile


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
            "%s Secret post_save signal received. instance: %s, created: %s",
            formatted_text("secret_post_save()"),
            instance,
            created,
        )
        new_secret_created.send(sender=Secret, instance=instance)
    else:
        logger.info(
            "%s Secret post_save signal received. instance: %s, created: %s",
            formatted_text("secret_post_save()"),
            instance,
            created,
        )
        secret_edited.send(sender=Secret, instance=instance)


@receiver(new_secret_created)
def new_secret_created_receiver(sender, instance, **kwargs):
    """Signal receiver for new_secret_created signal."""
    logger.info(
        "%s New secret created signal received. instance: %s",
        formatted_text("new_secret_created_receiver()"),
        instance,
    )


@receiver(secret_edited)
def secret_edited_receiver(sender, instance, **kwargs):
    """Signal receiver for secret_edited signal."""
    logger.info(
        "%s Secret edited signal received. instance: %s",
        formatted_text("secret_edited_receiver()"),
        instance,
    )
