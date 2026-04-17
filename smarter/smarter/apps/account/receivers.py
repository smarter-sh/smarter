# pylint: disable=unused-argument
"""Django signal receivers for account app."""

import logging

from django.contrib.auth.signals import user_logged_in
from django.core import serializers
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from smarter.apps.dashboard.context_processors import cache_invalidations
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import AbstractBroker

from .models import Account, Charge, DailyBillingRecord, User, UserProfile
from .signals import (
    broker_ready,
)
from .utils import get_cached_default_account


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


module_prefix = f"{__name__}"


@receiver(user_logged_in)
def user_logged_in_receiver(sender, request, user: User, **kwargs):
    """
    Signal receiver for user login.
    - verify that a UserProfile record exists for the user.
      if not, create one with the default account.
    """
    logger.info("%s User logged in: %s", formatted_text(f"{module_prefix}.user_logged_in()"), user)
    try:
        UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        account = get_cached_default_account()
        UserProfile.objects.create(name=user.username, user=user, account=account)
        logger.info("Created UserProfile for user: %s with default account: %s", user, account)
    except UserProfile.MultipleObjectsReturned:
        # this is fine. the same user can have multiple UserProfiles if they belong to multiple accounts
        pass


@receiver(post_save, sender=User)
def user_post_save(sender: User, instance: User, created, **kwargs):
    """
    Signal receiver for created/saved of User model.
    Assumed to be called on all logins since Django's
    default behavior is to update the last_login field on
    each login, which triggers a save.
    """
    logger.info(
        "%s User post_save: %s, created: %s",
        formatted_text(f"{module_prefix}.user_post_save()"),
        instance,
        created,
    )
    try:
        user_profile = UserProfile.get_cached_object(user=instance)
        cache_invalidations(user_profile=user_profile)
    except UserProfile.DoesNotExist:
        pass
    except UserProfile.MultipleObjectsReturned:
        # this is fine. the same user can have multiple UserProfiles if they belong to multiple accounts
        pass


@receiver(post_delete, sender=User)
def user_post_delete(sender: User, instance: User, **kwargs):
    """Signal receiver for deleted of User model."""
    logger.info(
        "%s User post_delete: %s, id: %s",
        formatted_text(f"{module_prefix}.user_post_delete()"),
        instance,
        instance.id,  # type: ignore
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


@receiver(post_delete, sender=UserProfile)
def user_profile_post_delete(sender: UserProfile, instance: UserProfile, **kwargs):
    """Signal receiver for deleted of UserProfile model."""
    logger.info(
        "%s UserProfile: %s, id: %s",
        formatted_text(f"{module_prefix}.user_profile_post_delete()"),
        instance,
        instance.id,  # type: ignore
    )


@receiver(post_save, sender=Account)
def account_post_save(sender: Account, instance: Account, created, **kwargs):
    """Signal receiver for created/saved of Account model."""
    model_prefix = formatted_text(f"{module_prefix}.account_post_save()")
    account_json = json.dumps(model_to_dict(instance))
    if created:
        logger.info("%s Account created: %s", model_prefix, account_json)
    else:
        logger.info("%s Account updated: %s", model_prefix, account_json)
        logger.info(
            "%s invalidating cache for Account: %s", formatted_text(f"{module_prefix}.account_post_save()"), instance
        )


@receiver(post_delete, sender=Account)
def account_post_delete(sender: Account, instance: Account, **kwargs):
    """Signal receiver for deleted of Account model."""
    logger.info(
        "%s Account post_delete: %s, id: %s",
        formatted_text(f"{module_prefix}.account_post_delete()"),
        instance,
        instance.id,  # type: ignore
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
