# pylint: disable=unused-argument
"""Django signal receivers for account app."""

from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Account, Charge, User, UserProfile
from .signals import (
    cache_invalidate,
    charge_authorized,
    charge_declined,
    new_charge_created,
    new_user_created,
)
from .utils import get_cached_default_account

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.RECEIVER_LOGGING, SmarterWaffleSwitches.ACCOUNT_LOGGING]
)

module_prefix = f"{__name__}"


@receiver(new_user_created)
def new_user_created_receiver(sender, user_profile: UserProfile, **kwargs):
    """
    Signal receiver for new_user_created signal.

    - log the creation of a new user profile.
    """
    logger.info(
        "%s New user created: %s, id: %s",
        logging.formatted_text(f"{module_prefix}.new_user_created_receiver()"),
        user_profile,
        user_profile.id,  # type: ignore
    )


@receiver(new_charge_created)
def new_charge_created_receiver(sender, charge: Charge, **kwargs):
    """
    Signal receiver for new_charge_created signal.

    - log the creation of a new charge.
    """
    logger.debug(
        "%s New charge created: %s, id: %s",
        logging.formatted_text(f"{module_prefix}.new_charge_created()"),
        charge,
        charge.id,  # type: ignore
    )


@receiver(cache_invalidate)
def cache_invalidate_receiver(sender, **kwargs):
    """
    Signal receiver for cache_invalidate signal.

    - log the cache invalidation event.
    """
    logger.debug(
        "%s Cache invalidation triggered.",
        logging.formatted_text(f"{module_prefix}.cache_invalidate()"),
    )


@receiver(charge_authorized)
def charge_authorized_receiver(sender, record_locator: str, charge: str, **kwargs):
    """
    Signal receiver for charge_authorized signal.

    - log the authorization of a charge.
    """
    logger.info(
        "%s Charge authorized: record_locator: %s, charge: %s",
        logging.formatted_text(f"{module_prefix}.charge_authorized()"),
        record_locator,
        charge,
    )


@receiver(charge_declined)
def charge_declined_receiver(sender, record_locator: str, charge: str, **kwargs):
    """
    Signal receiver for charge_declined signal.

    - log the decline of a charge.
    """
    logger.error(
        "%s Charge declined: record_locator: %s, charge: %s",
        logging.formatted_text(f"{module_prefix}.charge_declined()"),
        record_locator,
        charge,
    )


@receiver(user_logged_in)
def user_logged_in_receiver(sender, request, user: User, **kwargs):
    """
    Signal receiver for user login.

    - verify that a UserProfile record exists for the user.
      if not, create one with the default account.
    """
    logger.info("%s User logged in: %s", logging.formatted_text(f"{module_prefix}.user_logged_in()"), user)
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
    # pylint: disable=C0415
    from smarter.apps.dashboard.context_processors import cache_invalidations

    logger.info(
        "%s User post_save: %s, created: %s",
        logging.formatted_text(f"{module_prefix}.user_post_save()"),
        instance,
        created,
    )
    user_profiles = UserProfile.objects.filter(user=instance)
    for user_profile in user_profiles:
        cache_invalidations(user_profile=user_profile)


@receiver(post_delete, sender=User)
def user_post_delete(sender: User, instance: User, **kwargs):
    """Signal receiver for deleted of User model."""
    logger.info(
        "%s User post_delete: %s, id: %s",
        logging.formatted_text(f"{module_prefix}.user_post_delete()"),
        instance,
        instance.id,  # type: ignore
    )


@receiver(post_save, sender=UserProfile)
def user_profile_post_save(sender: UserProfile, instance: UserProfile, created, **kwargs):
    """Signal receiver for created/saved of UserProfile model."""
    logger.info(
        "%s UserProfile post_save: %s, created: %s",
        logging.formatted_text(f"{module_prefix}.user_profile_post_save()"),
        instance,
        created,
    )


@receiver(post_delete, sender=UserProfile)
def user_profile_post_delete(sender: UserProfile, instance: UserProfile, **kwargs):
    """Signal receiver for deleted of UserProfile model."""
    logger.info(
        "%s UserProfile: %s, id: %s",
        logging.formatted_text(f"{module_prefix}.user_profile_post_delete()"),
        instance,
        instance.id,  # type: ignore
    )


@receiver(post_save, sender=Account)
def account_post_save(sender: Account, instance: Account, created, **kwargs):
    """Signal receiver for created/saved of Account model."""
    model_prefix = logging.formatted_text(f"{module_prefix}.account_post_save()")
    account_json = json.dumps(model_to_dict(instance))
    if created:
        logger.info("%s Account created: %s", model_prefix, account_json)
    else:
        logger.info("%s Account updated: %s", model_prefix, account_json)
        logger.info(
            "%s invalidating cache for Account: %s",
            logging.formatted_text(f"{module_prefix}.account_post_save()"),
            instance,
        )


@receiver(post_delete, sender=Account)
def account_post_delete(sender: Account, instance: Account, **kwargs):
    """Signal receiver for deleted of Account model."""
    logger.info(
        "%s Account post_delete: %s, id: %s",
        logging.formatted_text(f"{module_prefix}.account_post_delete()"),
        instance,
        instance.id,  # type: ignore
    )


@receiver(post_save, sender=Charge)
def charge_post_save(sender: Charge, instance: Charge, created, **kwargs):
    """Signal receiver for created/saved of Charge model."""
    charge_json = json.dumps(model_to_dict(instance))
    logger.debug(
        "%s Charge post_save: %s, created: %s",
        logging.formatted_text(f"{module_prefix}.charge_post_save()"),
        charge_json,
        created,
    )
