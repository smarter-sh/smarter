# pylint: disable=W0613,W0212
"""
Cache management utilities for Vectorsearch objects.

This module provides functions for efficient type-annotated retrieval and
caching of Vectorsearch querysets. It includes utilities to:

- Retrieve and cache Vectorsearchs owned by a user profile
- Retrieve and cache Vectorsearchs shared with a user profile
- Retrieve and cache Vectorsearchs available to a user profile (owned or shared)
- Invalidate caches for owned, shared, and available Vectorsearchs
- Invalidate all Vectorsearch-related caches for a user profile

Functions:

    - get_cached_vectorsearchs_owned_by_user_profile(user_profile)
    - invalidate_cached_vectorsearchs_owned_by_user_profile(user_profile)
    - get_cached_vectorsearchs_shared_with_user_profile(user_profile)
    - invalidate_cached_vectorsearchs_shared_with_user_profile(user_profile)
    - get_cached_vectorsearchs_available_to_user_profile(user_profile)
    - invalidate_cached_vectorsearchs_available_to_user_profile(user_profile)
    - invalidate_all_cached_vectorsearchs_for_user_profile(user_profile)

Dependencies:

    - Django ORM
    - smarter.lib.cache.cache_results
    - smarter.apps.account.models.user_profile.UserProfile
    - smarter.apps.vectorsearch.models.Vectorsearch
    - smarter.apps.vectorsearch.serializers.VectorsearchSerializer
"""

from django.db import models

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Vectorsearch
from .serializers import VectorsearchSerializer

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.VECTORSEARCH_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@cache_results()
def _get_cached_vectorsearchs_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[Vectorsearch]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Vectorsearch.objects.owned_by(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching Vectorsearchs: %s",
        logger_prefix,
        logging.formatted_json(VectorsearchSerializer(retval, many=True).data),
    )
    return retval


def get_cached_vectorsearchs_owned_by_user_profile(user_profile: UserProfile) -> models.QuerySet[Vectorsearch]:
    """
    Retrieve the Vectorsearchs owned by the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Vectorsearch objects that are owned by the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose owned Vectorsearchs should be retrieved.
    :type user_profile: UserProfile

    :returns: A Django queryset containing the Vectorsearch objects owned by the user.
    :rtype: QuerySet[Vectorsearch]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> vectorsearchs = get_cached_vectorsearchs_owned_by_user_profile(user_profile)
        >>> for bot in vectorsearchs:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_vectorsearchs_owned_by_user_profile` - Invalidate the cache for owned Vectorsearchs of a user profile.
    """

    return _get_cached_vectorsearchs_owned_by_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_vectorsearchs_owned_by_user_profile(user_profile: UserProfile) -> None:
    _get_cached_vectorsearchs_owned_by_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_vectorsearchs_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[Vectorsearch]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Vectorsearch.objects.shared_with(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching Vectorsearchs: %s",
        logger_prefix,
        logging.formatted_json(VectorsearchSerializer(retval, many=True).data),
    )
    return retval


def get_cached_vectorsearchs_shared_with_user_profile(user_profile: UserProfile) -> models.QuerySet[Vectorsearch]:
    """
    Retrieve the Vectorsearchs shared with the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Vectorsearch objects that are shared with the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose shared Vectorsearchs should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the Vectorsearch objects shared with the user.
    :rtype: QuerySet[Vectorsearch]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> shared_vectorsearchs = get_cached_vectorsearchs_shared_with_user_profile(user_profile)
        >>> for bot in shared_vectorsearchs:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_vectorsearchs_shared_with_user_profile` - Invalidate the cache for shared Vectorsearchs of a user profile.
    """

    return _get_cached_vectorsearchs_shared_with_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_vectorsearchs_shared_with_user_profile(user_profile: UserProfile) -> None:
    _get_cached_vectorsearchs_shared_with_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_vectorsearchs_available_to_user_profile(user_profile_id) -> models.QuerySet[Vectorsearch]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Vectorsearch.objects.with_read_permission_for(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching Vectorsearchs: %s",
        logger_prefix,
        logging.formatted_json(VectorsearchSerializer(retval, many=True).data),
    )
    return retval


def get_cached_vectorsearchs_available_to_user_profile(user_profile: UserProfile) -> models.QuerySet[Vectorsearch]:
    """
    Retrieve the Vectorsearchs available to the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Vectorsearch objects that are available to the specified user profile,
    which may include both owned and shared Vectorsearchs. The results are cached to reduce database queries
    and improve performance. If the cache is invalidated, the queryset is fetched from the database again
    and re-cached.

    :param user_profile: The user profile whose available Vectorsearchs should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the Vectorsearch objects available to the user.
    :rtype: QuerySet[Vectorsearch]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> available_vectorsearchs = get_cached_vectorsearchs_available_to_user_profile(user_profile)
        >>> for bot in available_vectorsearchs:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_vectorsearchs_available_to_user_profile` - Invalidate the cache for available Vectorsearchs of a user profile.
    """

    return _get_cached_vectorsearchs_available_to_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_vectorsearchs_available_to_user_profile(user_profile: UserProfile) -> None:
    _get_cached_vectorsearchs_available_to_user_profile.invalidate(user_profile.id)  # type: ignore


def invalidate_all_cached_vectorsearchs_for_user_profile(user_profile: UserProfile) -> None:
    """
    Invalidate all cached Vectorsearch querysets related to the given UserProfile.

    This function invalidates the caches for all Vectorsearch querysets that are related to the specified user profile,
    including owned, shared, and available Vectorsearchs. This is useful when a change occurs that may
    affect any of these querysets, ensuring that subsequent calls will fetch fresh data from the database.

    :param user_profile: The user profile for which to invalidate cached Vectorsearch querysets.
    :type user_profile: UserProfile
    :returns: None
    :rtype: None

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> invalidate_all_cached_vectorsearchs_for_user_profile(user_profile)

    .. seealso::

        - :func:`invalidate_cached_vectorsearchs_owned_by_user_profile` - Invalidate the cache for owned Vectorsearchs of a user profile.
        - :func:`invalidate_cached_vectorsearchs_shared_with_user_profile` - Invalidate the cache for shared Vectorsearchs of a user profile.
        - :func:`invalidate_cached_vectorsearchs_available_to_user_profile` - Invalidate the cache for available Vectorsearchs of a user profile.
    """
    invalidate_cached_vectorsearchs_owned_by_user_profile(user_profile=user_profile)
    invalidate_cached_vectorsearchs_shared_with_user_profile(user_profile=user_profile)
    invalidate_cached_vectorsearchs_available_to_user_profile(user_profile=user_profile)
