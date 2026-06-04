# pylint: disable=W0613,W0212
"""
Cache management utilities for Secret objects.

This module provides functions for efficient type-annotated retrieval and
caching of Secret querysets. It includes utilities to:

- Retrieve and cache Secrets owned by a user profile
- Retrieve and cache Secrets shared with a user profile
- Retrieve and cache Secrets available to a user profile (owned or shared)
- Invalidate caches for owned, shared, and available Secrets
- Invalidate all Secret-related caches for a user profile

Functions:

    - get_cached_secrets_owned_by_user_profile(user_profile)
    - invalidate_cached_secrets_owned_by_user_profile(user_profile)
    - get_cached_secrets_shared_with_user_profile(user_profile)
    - invalidate_cached_secrets_shared_with_user_profile(user_profile)
    - get_cached_secrets_available_to_user_profile(user_profile)
    - invalidate_cached_secrets_available_to_user_profile(user_profile)
    - invalidate_all_cached_secrets_for_user_profile(user_profile)

Dependencies:

    - Django ORM
    - smarter.lib.cache.cache_results
    - smarter.apps.account.models.user_profile.UserProfile
    - smarter.apps.secret.models.Secret
    - smarter.apps.secret.serializers.SecretSerializer

"""

from django.db import models

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Secret
from .serializers import SecretSerializer

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.SECRET_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@cache_results()
def _get_cached_secrets_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[Secret]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Secret.objects.owned_by(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching Secrets owned by user: %s",
        logger_prefix,
        logging.formatted_json(SecretSerializer(retval, many=True).data),
    )
    return retval


def get_cached_secrets_owned_by_user_profile(user_profile: UserProfile) -> models.QuerySet[Secret]:
    """
    Retrieve the Secrets owned by the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Secret objects that are owned by the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose owned Secrets should be retrieved.
    :type user_profile: UserProfile

    :returns: A Django queryset containing the Secret objects owned by the user.
    :rtype: QuerySet[Secret]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> secrets = get_cached_secrets_owned_by_user_profile(user_profile)
        >>> for bot in secrets:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_secrets_owned_by_user_profile` - Invalidate the cache for owned Secrets of a user profile.
    """

    return _get_cached_secrets_owned_by_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_secrets_owned_by_user_profile(user_profile: UserProfile) -> None:
    _get_cached_secrets_owned_by_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_secrets_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[Secret]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Secret.objects.shared_with(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching Secrets shared with user: %s",
        logger_prefix,
        logging.formatted_json(SecretSerializer(retval, many=True).data),
    )
    return retval


def get_cached_secrets_shared_with_user_profile(user_profile: UserProfile) -> models.QuerySet[Secret]:
    """
    Retrieve the Secrets shared with the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Secret objects that are shared with the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose shared Secrets should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the Secret objects shared with the user.
    :rtype: QuerySet[Secret]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> shared_secrets = get_cached_secrets_shared_with_user_profile(user_profile)
        >>> for bot in shared_secrets:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_secrets_shared_with_user_profile` - Invalidate the cache for shared Secrets of a user profile.
    """

    return _get_cached_secrets_shared_with_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_secrets_shared_with_user_profile(user_profile: UserProfile) -> None:
    _get_cached_secrets_shared_with_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_secrets_available_to_user_profile(user_profile_id) -> models.QuerySet[Secret]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Secret.objects.with_read_permission_for(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching Secrets available to user: %s",
        logger_prefix,
        logging.formatted_json(SecretSerializer(retval, many=True).data),
    )
    return retval


def get_cached_secrets_available_to_user_profile(user_profile: UserProfile) -> models.QuerySet[Secret]:
    """
    Retrieve the Secrets available to the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Secret objects that are available to the specified user profile,
    which may include both owned and shared Secrets. The results are cached to reduce database queries
    and improve performance. If the cache is invalidated, the queryset is fetched from the database again
    and re-cached.

    :param user_profile: The user profile whose available Secrets should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the Secret objects available to the user.
    :rtype: QuerySet[Secret]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> available_secrets = get_cached_secrets_available_to_user_profile(user_profile)
        >>> for bot in available_secrets:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_secrets_available_to_user_profile` - Invalidate the cache for available Secrets of a user profile.
    """

    return _get_cached_secrets_available_to_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_secrets_available_to_user_profile(user_profile: UserProfile) -> None:
    _get_cached_secrets_available_to_user_profile.invalidate(user_profile.id)  # type: ignore


def invalidate_all_cached_secrets_for_user_profile(user_profile: UserProfile) -> None:
    """
    Invalidate all cached Secret querysets related to the given UserProfile.

    This function invalidates the caches for all Secret querysets that are related to the specified user profile,
    including owned, shared, and available Secrets. This is useful when a change occurs that may
    affect any of these querysets, ensuring that subsequent calls will fetch fresh data from the database.

    :param user_profile: The user profile for which to invalidate cached Secret querysets.
    :type user_profile: UserProfile
    :returns: None
    :rtype: None

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> invalidate_all_cached_secrets_for_user_profile(user_profile)

    .. seealso::

        - :func:`invalidate_cached_secrets_owned_by_user_profile` - Invalidate the cache for owned Secrets of a user profile.
        - :func:`invalidate_cached_secrets_shared_with_user_profile` - Invalidate the cache for shared Secrets of a user profile.
        - :func:`invalidate_cached_secrets_available_to_user_profile` - Invalidate the cache for available Secrets of a user profile.
    """
    invalidate_cached_secrets_owned_by_user_profile(user_profile=user_profile)
    invalidate_cached_secrets_shared_with_user_profile(user_profile=user_profile)
    invalidate_cached_secrets_available_to_user_profile(user_profile=user_profile)
