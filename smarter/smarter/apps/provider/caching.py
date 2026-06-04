# pylint: disable=W0613,W0212
"""
Cache management utilities for Provider objects.

This module provides functions for efficient type-annotated retrieval and
caching of Provider querysets. It includes utilities to:

- Retrieve and cache Providers owned by a user profile
- Retrieve and cache Providers shared with a user profile
- Retrieve and cache Providers available to a user profile (owned or shared)
- Invalidate caches for owned, shared, and available Providers
- Invalidate all Provider-related caches for a user profile

Functions:

    - get_cached_providers_owned_by_user_profile(user_profile)
    - invalidate_cached_providers_owned_by_user_profile(user_profile)
    - get_cached_providers_shared_with_user_profile(user_profile)
    - invalidate_cached_providers_shared_with_user_profile(user_profile)
    - get_cached_providers_available_to_user_profile(user_profile)
    - invalidate_cached_providers_available_to_user_profile(user_profile)
    - invalidate_all_cached_providers_for_user_profile(user_profile)

Dependencies:

    - Django ORM
    - smarter.lib.cache.cache_results
    - smarter.apps.account.models.user_profile.UserProfile
    - smarter.apps.provider.models.Provider
    - smarter.apps.provider.serializers.ProviderSerializer

"""

from django.db import models

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Provider
from .serializers import ProviderSerializer

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.PROVIDER_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@cache_results()
def _get_cached_providers_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[Provider]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Provider.objects.owned_by(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching Providers owned by user: %s",
        logger_prefix,
        logging.formatted_json(ProviderSerializer(retval, many=True).data),
    )
    return retval


def get_cached_providers_owned_by_user_profile(user_profile: UserProfile) -> models.QuerySet[Provider]:
    """
    Retrieve the Providers owned by the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Provider objects that are owned by the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose owned Providers should be retrieved.
    :type user_profile: UserProfile

    :returns: A Django queryset containing the Provider objects owned by the user.
    :rtype: QuerySet[Provider]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> providers = get_cached_providers_owned_by_user_profile(user_profile)
        >>> for bot in providers:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_providers_owned_by_user_profile` - Invalidate the cache for owned Providers of a user profile.
    """

    return _get_cached_providers_owned_by_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_providers_owned_by_user_profile(user_profile: UserProfile) -> None:
    _get_cached_providers_owned_by_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_providers_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[Provider]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Provider.objects.shared_with(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching Providers shared with user: %s",
        logger_prefix,
        logging.formatted_json(ProviderSerializer(retval, many=True).data),
    )
    return retval


def get_cached_providers_shared_with_user_profile(user_profile: UserProfile) -> models.QuerySet[Provider]:
    """
    Retrieve the Providers shared with the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Provider objects that are shared with the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose shared Providers should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the Provider objects shared with the user.
    :rtype: QuerySet[Provider]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> shared_providers = get_cached_providers_shared_with_user_profile(user_profile)
        >>> for bot in shared_providers:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_providers_shared_with_user_profile` - Invalidate the cache for shared Providers of a user profile.
    """

    return _get_cached_providers_shared_with_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_providers_shared_with_user_profile(user_profile: UserProfile) -> None:
    _get_cached_providers_shared_with_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_providers_available_to_user_profile(user_profile_id) -> models.QuerySet[Provider]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Provider.objects.with_read_permission_for(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching Providers available to user: %s",
        logger_prefix,
        logging.formatted_json(ProviderSerializer(retval, many=True).data),
    )
    return retval


def get_cached_providers_available_to_user_profile(user_profile: UserProfile) -> models.QuerySet[Provider]:
    """
    Retrieve the Providers available to the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Provider objects that are available to the specified user profile,
    which may include both owned and shared Providers. The results are cached to reduce database queries
    and improve performance. If the cache is invalidated, the queryset is fetched from the database again
    and re-cached.

    :param user_profile: The user profile whose available Providers should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the Provider objects available to the user.
    :rtype: QuerySet[Provider]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> available_providers = get_cached_providers_available_to_user_profile(user_profile)
        >>> for bot in available_providers:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_providers_available_to_user_profile` - Invalidate the cache for available Providers of a user profile.
    """

    return _get_cached_providers_available_to_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_providers_available_to_user_profile(user_profile: UserProfile) -> None:
    _get_cached_providers_available_to_user_profile.invalidate(user_profile.id)  # type: ignore


def invalidate_all_cached_providers_for_user_profile(user_profile: UserProfile) -> None:
    """
    Invalidate all cached Provider querysets related to the given UserProfile.

    This function invalidates the caches for all Provider querysets that are related to the specified user profile,
    including owned, shared, and available Providers. This is useful when a change occurs that may
    affect any of these querysets, ensuring that subsequent calls will fetch fresh data from the database.

    :param user_profile: The user profile for which to invalidate cached Provider querysets.
    :type user_profile: UserProfile
    :returns: None
    :rtype: None

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> invalidate_all_cached_providers_for_user_profile(user_profile)

    .. seealso::

        - :func:`invalidate_cached_providers_owned_by_user_profile` - Invalidate the cache for owned Providers of a user profile.
        - :func:`invalidate_cached_providers_shared_with_user_profile` - Invalidate the cache for shared Providers of a user profile.
        - :func:`invalidate_cached_providers_available_to_user_profile` - Invalidate the cache for available Providers of a user profile.
    """
    invalidate_cached_providers_owned_by_user_profile(user_profile=user_profile)
    invalidate_cached_providers_shared_with_user_profile(user_profile=user_profile)
    invalidate_cached_providers_available_to_user_profile(user_profile=user_profile)
