# pylint: disable=W0613,W0212
"""
Cache management utilities for Proxy objects.

This module provides functions for efficient type-annotated retrieval and
caching of Proxy querysets. It includes utilities to:

- Retrieve and cache Proxies owned by a user profile
- Retrieve and cache Proxies shared with a user profile
- Retrieve and cache Proxies available to a user profile (owned or shared)
- Invalidate caches for owned, shared, and available Proxies
- Invalidate all Proxy-related caches for a user profile

Functions:

    - get_cached_proxies_owned_by_user_profile(user_profile)
    - invalidate_cached_proxies_owned_by_user_profile(user_profile)
    - get_cached_proxies_shared_with_user_profile(user_profile)
    - invalidate_cached_proxies_shared_with_user_profile(user_profile)
    - get_cached_proxies_available_to_user_profile(user_profile)
    - invalidate_cached_proxies_available_to_user_profile(user_profile)
    - invalidate_all_cached_proxies_for_user_profile(user_profile)

Dependencies:

    - Django ORM
    - smarter.lib.cache.cache_results
    - smarter.apps.account.models.user_profile.UserProfile
    - smarter.apps.proxy.models.Proxy
    - smarter.apps.proxy.serializers.ProxySerializer
"""

from django.db import models

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Proxy
from .serializers import ProxySerializer

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.SECRET_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@cache_results()
def _get_cached_proxies_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[Proxy]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Proxy.objects.owned_by(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching Proxies owned by user: %s",
        logger_prefix,
        logging.formatted_json(ProxySerializer(retval, many=True).data),
    )
    return retval


def get_cached_proxies_owned_by_user_profile(user_profile: UserProfile) -> models.QuerySet[Proxy]:
    """
    Retrieve the Proxies owned by the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Proxy objects that are owned by the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose owned Proxies should be retrieved.
    :type user_profile: UserProfile

    :returns: A Django queryset containing the Proxy objects owned by the user.
    :rtype: QuerySet[Proxy]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> proxies = get_cached_proxies_owned_by_user_profile(user_profile)
        >>> for bot in proxies:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_proxies_owned_by_user_profile` - Invalidate the cache for owned Proxies of a user profile.
    """

    return _get_cached_proxies_owned_by_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_proxies_owned_by_user_profile(user_profile: UserProfile) -> None:
    _get_cached_proxies_owned_by_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_proxies_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[Proxy]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Proxy.objects.shared_with(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching Proxies shared with user: %s",
        logger_prefix,
        logging.formatted_json(ProxySerializer(retval, many=True).data),
    )
    return retval


def get_cached_proxies_shared_with_user_profile(user_profile: UserProfile) -> models.QuerySet[Proxy]:
    """
    Retrieve the Proxies shared with the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Proxy objects that are shared with the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose shared Proxies should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the Proxy objects shared with the user.
    :rtype: QuerySet[Proxy]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> shared_proxies = get_cached_proxies_shared_with_user_profile(user_profile)
        >>> for bot in shared_proxies:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_proxies_shared_with_user_profile` - Invalidate the cache for shared Proxies of a user profile.
    """

    return _get_cached_proxies_shared_with_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_proxies_shared_with_user_profile(user_profile: UserProfile) -> None:
    _get_cached_proxies_shared_with_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_proxies_available_to_user_profile(user_profile_id) -> models.QuerySet[Proxy]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Proxy.objects.with_read_permission_for(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching Proxies available to user: %s",
        logger_prefix,
        logging.formatted_json(ProxySerializer(retval, many=True).data),
    )
    return retval


def get_cached_proxies_available_to_user_profile(user_profile: UserProfile) -> models.QuerySet[Proxy]:
    """
    Retrieve the Proxies available to the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Proxy objects that are available to the specified user profile,
    which may include both owned and shared Proxies. The results are cached to reduce database queries
    and improve performance. If the cache is invalidated, the queryset is fetched from the database again
    and re-cached.

    :param user_profile: The user profile whose available Proxies should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the Proxy objects available to the user.
    :rtype: QuerySet[Proxy]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> available_proxies = get_cached_proxies_available_to_user_profile(user_profile)
        >>> for bot in available_proxies:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_proxies_available_to_user_profile` - Invalidate the cache for available Proxies of a user profile.
    """

    return _get_cached_proxies_available_to_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_proxies_available_to_user_profile(user_profile: UserProfile) -> None:
    _get_cached_proxies_available_to_user_profile.invalidate(user_profile.id)  # type: ignore


def invalidate_all_cached_proxies_for_user_profile(user_profile: UserProfile) -> None:
    """
    Invalidate all cached Proxy querysets related to the given UserProfile.

    This function invalidates the caches for all Proxy querysets that are related to the specified user profile,
    including owned, shared, and available Proxies. This is useful when a change occurs that may
    affect any of these querysets, ensuring that subsequent calls will fetch fresh data from the database.

    :param user_profile: The user profile for which to invalidate cached Proxy querysets.
    :type user_profile: UserProfile
    :returns: None
    :rtype: None

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> invalidate_all_cached_proxies_for_user_profile(user_profile)

    .. seealso::

        - :func:`invalidate_cached_proxies_owned_by_user_profile` - Invalidate the cache for owned Proxies of a user profile.
        - :func:`invalidate_cached_proxies_shared_with_user_profile` - Invalidate the cache for shared Proxies of a user profile.
        - :func:`invalidate_cached_proxies_available_to_user_profile` - Invalidate the cache for available Proxies of a user profile.
    """
    invalidate_cached_proxies_owned_by_user_profile(user_profile=user_profile)
    invalidate_cached_proxies_shared_with_user_profile(user_profile=user_profile)
    invalidate_cached_proxies_available_to_user_profile(user_profile=user_profile)
