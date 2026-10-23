# pylint: disable=unused-argument
"""Django signal receivers for account app."""

from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

from smarter.lib import json, logging
from smarter.lib.django.listview import LISTVIEW_CACHE_ALL, connect_listview_cache
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import (
    Account,
    Budget,
    Charge,
    ResourceConstraint,
    ResourceLock,
    User,
    UserProfile,
    active_language,
    evaluate_resource_constraints,
)
from .models.budget import get_resource_lock_message
from .signals import (
    budget_exceeded,
    budget_released,
    budget_warning,
    cache_invalidate,
    charge_authorized,
    charge_declined,
    new_charge_created,
    new_user_created,
)
from .utils import (
    get_cached_default_account,
    get_cached_user_for_user_id,
    get_cached_user_for_username,
)

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
    - evaluate the budgets attached to the charged resource.
    """
    logger.debug(
        "%s New charge created: %s, id: %s",
        logging.formatted_text(f"{module_prefix}.new_charge_created()"),
        charge,
        charge.id,  # type: ignore
    )
    evaluate_resource_constraints(charge.resource_locator)


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
    logger.debug(
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
      if not, create one with the default account, and the request's language, which the
      web console chose from the language cookie or the browser's Accept-Language header.
      This is how a console sign-up gets its UserProfile.
    """
    # SmarterTokenAuthenticationMiddleware logs the user in on every api request that carries a token,
    # so those logins are logged at DEBUG. A sign-in to the web console is logged at INFO.
    log = logger.debug if request is not None and request.META.get("HTTP_AUTHORIZATION") else logger.info
    log("%s User logged in: %s", logging.formatted_text(f"{module_prefix}.user_logged_in()"), user)
    try:
        UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        account = get_cached_default_account()
        UserProfile.objects.create(name=user.username, user=user, account=account, language=active_language())
        logger.info(
            "%s created a UserProfile for user %s with the default account %s",
            logging.formatted_text(f"{module_prefix}.user_logged_in()"),
            user,
            account,
        )
    except UserProfile.MultipleObjectsReturned:
        # this is fine. the same user can have multiple UserProfiles if they belong to multiple accounts
        pass


@receiver(post_save, sender=User)
def user_post_save(sender: User, instance: User, created, **kwargs):
    """
    Signal receiver for created/saved of User model.

    Invalidates the user's cached resources, except when the save only updated
    ``last_login``. Django saves ``last_login`` on each login, and
    SmarterTokenAuthenticationMiddleware logs the user in on every api request,
    so invalidating then would empty the user's caches on every request.
    """
    # pylint: disable=C0415
    from smarter.apps.dashboard.context_processors import cache_invalidations

    update_fields = kwargs.get("update_fields")
    last_login_only = bool(update_fields) and set(update_fields) == {"last_login"}
    # a save of last_login alone happens on every login, including every api request with a token.
    log = logger.debug if last_login_only else logger.info
    log(
        "%s User post_save: %s, created: %s",
        logging.formatted_text(f"{module_prefix}.user_post_save()"),
        instance,
        created,
    )
    if last_login_only:
        return
    get_cached_user_for_user_id(invalidate=True, user_id=instance.id)  # type: ignore[attr-defined]
    get_cached_user_for_username(invalidate=True, username=instance.username)
    if created:
        # A new User has no UserProfiles yet. Refreshing get_cached_objects() now would cache an
        # empty list, which would hide the UserProfile that is created next.
        return
    # The cached UserProfiles carry a copy of the User, e.g. is_staff, and cache_invalidations()
    # only refreshes the one cached by pk, so refresh the ones cached by user and by user and account.
    UserProfile.get_cached_objects(invalidate=True, user=instance)
    user_profiles = UserProfile.objects.filter(user=instance).select_related("account")
    for user_profile in user_profiles:
        UserProfile.get_cached_object(invalidate=True, user=instance, account=user_profile.account)
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
    # The user's cached list of UserProfiles, used by every permission queryset, changes with this one.
    UserProfile.get_cached_objects(invalidate=True, user=instance.user)


@receiver(post_delete, sender=UserProfile)
def user_profile_post_delete(sender: UserProfile, instance: UserProfile, **kwargs):
    """Signal receiver for deleted of UserProfile model."""
    logger.info(
        "%s UserProfile: %s, id: %s",
        logging.formatted_text(f"{module_prefix}.user_profile_post_delete()"),
        instance,
        instance.id,  # type: ignore
    )
    try:
        user = instance.user
    except User.DoesNotExist:
        # Deleted together with its User, whose cached profiles nobody can look up any more.
        return
    UserProfile.get_cached_objects(invalidate=True, user=user)


# an Account's contact details are personal data, which the logs must not hold.
ACCOUNT_CONTACT_FIELDS = ("phone_number", "address1", "address2", "city", "state", "postal_code")


@receiver(post_save, sender=Account)
def account_post_save(sender: Account, instance: Account, created, **kwargs):
    """Signal receiver for created/saved of Account model."""
    model_prefix = logging.formatted_text(f"{module_prefix}.account_post_save()")
    account_json = json.dumps(model_to_dict(instance, exclude=ACCOUNT_CONTACT_FIELDS))
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


@receiver(post_save, sender=Budget)
def budget_post_save(sender: Budget, instance: Budget, created, **kwargs):
    """Signal receiver for created/saved of Budget model.

    Changed limits apply at once.
    """
    for constraint in instance.constraints.filter(is_active=True):  # type: ignore[attr-defined]
        constraint.evaluate()


@receiver(post_save, sender=ResourceConstraint)
def resource_constraint_post_save(sender: ResourceConstraint, instance: ResourceConstraint, created, **kwargs):
    """Signal receiver for created/saved of ResourceConstraint model.

    A budget applies as soon as it is attached.
    """
    instance.evaluate()


@receiver(post_save, sender=ResourceLock)
@receiver(post_delete, sender=ResourceLock)
def resource_lock_changed(sender: ResourceLock, instance: ResourceLock, **kwargs):
    """Signal receiver for saved/deleted of ResourceLock model.

    charge_authorization() sees the change at once.
    """
    get_resource_lock_message.invalidate(instance.resource_locator)


@receiver(budget_warning)
def budget_warning_receiver(sender, resource_constraint: ResourceConstraint, actual, limit, **kwargs):
    """Signal receiver for budget_warning signal."""
    logger.warning(
        "%s Budget warning: %s has spent %s of its limit of %s.",
        logging.formatted_text(f"{module_prefix}.budget_warning()"),
        resource_constraint,
        actual,
        limit,
    )


@receiver(budget_exceeded)
def budget_exceeded_receiver(sender, resource_constraint: ResourceConstraint, lock, reason: str, **kwargs):
    """Signal receiver for budget_exceeded signal."""
    logger.warning(
        "%s Budget exceeded: %s %s %s",
        logging.formatted_text(f"{module_prefix}.budget_exceeded()"),
        resource_constraint,
        "is locked." if lock else "is not locked, because the budget only warns.",
        reason,
    )


@receiver(budget_released)
def budget_released_receiver(sender, resource_constraint: ResourceConstraint, **kwargs):
    """Signal receiver for budget_released signal."""
    logger.info(
        "%s Budget released: %s is no longer locked.",
        logging.formatted_text(f"{module_prefix}.budget_released()"),
        resource_constraint,
    )


# a user profile, an account or a resource's tags can change what every list shows: its owners,
# what each user may see, and the tags column.
connect_listview_cache(LISTVIEW_CACHE_ALL, "account.UserProfile", "account.Account", "taggit.TaggedItem")
