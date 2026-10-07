# pylint: disable=W0613,W0212
"""
Cache management utilities for ConnectionBase objects.

This module provides functions for efficient type-annotated retrieval and
caching of ConnectionBase querysets. It includes utilities to:

- Retrieve and cache Connections owned by a user profile
- Retrieve and cache Connections shared with a user profile
- Retrieve and cache Connections available to a user profile (owned or shared)
- Invalidate caches for owned, shared, and available Connections
- Invalidate all ConnectionBase-related caches for a user profile

Functions:

    - get_cached_connections_owned_by_user_profile(user_profile)
    - invalidate_cached_connections_owned_by_user_profile(user_profile)
    - get_cached_connections_shared_with_user_profile(user_profile)
    - invalidate_cached_connections_shared_with_user_profile(user_profile)
    - get_cached_connections_available_to_user_profile(user_profile)
    - invalidate_cached_connections_available_to_user_profile(user_profile)
    - invalidate_all_cached_connections_for_user_profile(user_profile)

Dependencies:

    - Django ORM
    - smarter.lib.cache.cache_results
    - smarter.apps.account.models.user_profile.UserProfile
    - smarter.apps.connection.models.ConnectionBase
    - smarter.apps.connection.serializers.ConnectionSerializer

"""

from django.db import models

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import ConnectionBase
from .serializers import ConnectionSerializer

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.CONNECTION_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@cache_results()
def _get_cached_connections_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[ConnectionBase]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = ConnectionBase.objects.owned_by(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching Connections owned by user: %s",
        logger_prefix,
        logging.formatted_json(ConnectionSerializer(retval, many=True).data),
    )
    return retval


def get_cached_connections_owned_by_user_profile(user_profile: UserProfile) -> models.QuerySet[ConnectionBase]:
    """
    Retrieve the Connections owned by the given UserProfile, using caching to optimize performance.

    This function returns a queryset of ConnectionBase objects that are owned by the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose owned Connections should be retrieved.
    :type user_profile: UserProfile

    :returns: A Django queryset containing the ConnectionBase objects owned by the user.
    :rtype: QuerySet[ConnectionBase]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> connections = get_cached_connections_owned_by_user_profile(user_profile)
        >>> for bot in connections:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_connections_owned_by_user_profile` - Invalidate the cache for owned Connections of a user profile.
    """

    return _get_cached_connections_owned_by_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_connections_owned_by_user_profile(user_profile: UserProfile) -> None:
    _get_cached_connections_owned_by_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_connections_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[ConnectionBase]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = ConnectionBase.objects.shared_with(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching Connections shared with user: %s",
        logger_prefix,
        logging.formatted_json(ConnectionSerializer(retval, many=True).data),
    )
    return retval


def get_cached_connections_shared_with_user_profile(user_profile: UserProfile) -> models.QuerySet[ConnectionBase]:
    """
    Retrieve the Connections shared with the given UserProfile, using caching to optimize performance.

    This function returns a queryset of ConnectionBase objects that are shared with the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose shared Connections should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the ConnectionBase objects shared with the user.
    :rtype: QuerySet[ConnectionBase]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> shared_connections = get_cached_connections_shared_with_user_profile(user_profile)
        >>> for bot in shared_connections:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_connections_shared_with_user_profile` - Invalidate the cache for shared Connections of a user profile.
    """

    return _get_cached_connections_shared_with_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_connections_shared_with_user_profile(user_profile: UserProfile) -> None:
    _get_cached_connections_shared_with_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_connections_available_to_user_profile(user_profile_id) -> models.QuerySet[ConnectionBase]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = ConnectionBase.objects.with_read_permission_for(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching Connections available to user: %s",
        logger_prefix,
        logging.formatted_json(ConnectionSerializer(retval, many=True).data),
    )
    return retval


def get_cached_connections_available_to_user_profile(user_profile: UserProfile) -> models.QuerySet[ConnectionBase]:
    """
    Retrieve the Connections available to the given UserProfile, using caching to optimize performance.

    This function returns a queryset of ConnectionBase objects that are available to the specified user profile,
    which may include both owned and shared Connections. The results are cached to reduce database queries
    and improve performance. If the cache is invalidated, the queryset is fetched from the database again
    and re-cached.

    :param user_profile: The user profile whose available Connections should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the ConnectionBase objects available to the user.
    :rtype: QuerySet[ConnectionBase]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> available_connections = get_cached_connections_available_to_user_profile(user_profile)
        >>> for bot in available_connections:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_connections_available_to_user_profile` - Invalidate the cache for available Connections of a user profile.
    """

    return _get_cached_connections_available_to_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_connections_available_to_user_profile(user_profile: UserProfile) -> None:
    _get_cached_connections_available_to_user_profile.invalidate(user_profile.id)  # type: ignore


def invalidate_all_cached_connections_for_user_profile(user_profile: UserProfile) -> None:
    """
    Invalidate all cached ConnectionBase querysets related to the given UserProfile.

    This function invalidates the caches for all ConnectionBase querysets that are related to the specified user profile,
    including owned, shared, and available Connections. This is useful when a change occurs that may
    affect any of these querysets, ensuring that subsequent calls will fetch fresh data from the database.

    :param user_profile: The user profile for which to invalidate cached ConnectionBase querysets.
    :type user_profile: UserProfile
    :returns: None
    :rtype: None

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> invalidate_all_cached_connections_for_user_profile(user_profile)

    .. seealso::

        - :func:`invalidate_cached_connections_owned_by_user_profile` - Invalidate the cache for owned Connections of a user profile.
        - :func:`invalidate_cached_connections_shared_with_user_profile` - Invalidate the cache for shared Connections of a user profile.
        - :func:`invalidate_cached_connections_available_to_user_profile` - Invalidate the cache for available Connections of a user profile.
    """
    invalidate_cached_connections_owned_by_user_profile(user_profile=user_profile)
    invalidate_cached_connections_shared_with_user_profile(user_profile=user_profile)
    invalidate_cached_connections_available_to_user_profile(user_profile=user_profile)
