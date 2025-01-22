# pylint: disable=unused-argument
"""Django signal receivers for account app."""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Account, Charge, DailyBillingRecord, UserProfile


logger = logging.getLogger(__name__)


@receiver(post_save, sender=UserProfile)
def user_profile_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of UserProfile model."""
    if created:
        logger.debug("""UserProfile post_save signal received. instance: %s, created: %s""", instance, created)


@receiver(post_save, sender=Account)
def account_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of Account model."""
    if created:
        logger.debug("""Account post_save signal received. instance: %s, created: %s""", instance, created)


@receiver(post_save, sender=Charge)
def charge_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of Charge model."""
    if created:
        logger.debug("""Charge post_save signal received. instance: %s, created: %s""", instance, created)


@receiver(post_save, sender=DailyBillingRecord)
def daily_billing_record_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of DailyBillingRecord model."""
    if created:
        logger.debug("""DailyBillingRecord post_save signal received. instance: %s, created: %s""", instance, created)
