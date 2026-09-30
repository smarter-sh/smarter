# pylint: disable=W0613,W0212
"""
Cache management utilities for LLMHost objects.

This module provides functions for efficient type-annotated retrieval and
caching of LLMHost querysets. It includes utilities to:

- Retrieve and cache LLMHosts owned by a user profile
- Retrieve and cache LLMHosts shared with a user profile
- Retrieve and cache LLMHosts available to a user profile (owned or shared)
- Invalidate caches for owned, shared, and available LLMHosts
- Invalidate all LLMHost-related caches for a user profile

Functions:

    - get_cached_llmhosts_owned_by_user_profile(user_profile)
    - invalidate_cached_llmhosts_owned_by_user_profile(user_profile)
    - get_cached_llmhosts_shared_with_user_profile(user_profile)
    - invalidate_cached_llmhosts_shared_with_user_profile(user_profile)
    - get_cached_llmhosts_available_to_user_profile(user_profile)
    - invalidate_cached_llmhosts_available_to_user_profile(user_profile)
    - invalidate_all_cached_llmhosts_for_user_profile(user_profile)

Dependencies:

    - Django ORM
    - smarter.lib.cache.cache_results
    - smarter.apps.account.models.user_profile.UserProfile
    - smarter.apps.llmhost.models.LLMHost
    - smarter.apps.llmhost.serializers.LLMHostSerializer
"""

from django.db import models

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import LLMHost
from .serializers import LLMHostSerializer

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@cache_results()
def _get_cached_llmhosts_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[LLMHost]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = LLMHost.objects.owned_by(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching LLMHosts: %s",
        logger_prefix,
        logging.formatted_json(LLMHostSerializer(retval, many=True).data),
    )
    return retval


def get_cached_llmhosts_owned_by_user_profile(user_profile: UserProfile) -> models.QuerySet[LLMHost]:
    """
    Retrieve the LLMHosts owned by the given UserProfile, using caching to optimize performance.

    This function returns a queryset of LLMHost objects that are owned by the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose owned LLMHosts should be retrieved.
    :type user_profile: UserProfile

    :returns: A Django queryset containing the LLMHost objects owned by the user.
    :rtype: QuerySet[LLMHost]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> llmhosts = get_cached_llmhosts_owned_by_user_profile(user_profile)
        >>> for bot in llmhosts:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_llmhosts_owned_by_user_profile` - Invalidate the cache for owned LLMHosts of a user profile.
    """

    return _get_cached_llmhosts_owned_by_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_llmhosts_owned_by_user_profile(user_profile: UserProfile) -> None:
    _get_cached_llmhosts_owned_by_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_llmhosts_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[LLMHost]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = LLMHost.objects.shared_with(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching LLMHosts: %s",
        logger_prefix,
        logging.formatted_json(LLMHostSerializer(retval, many=True).data),
    )
    return retval


def get_cached_llmhosts_shared_with_user_profile(user_profile: UserProfile) -> models.QuerySet[LLMHost]:
    """
    Retrieve the LLMHosts shared with the given UserProfile, using caching to optimize performance.

    This function returns a queryset of LLMHost objects that are shared with the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose shared LLMHosts should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the LLMHost objects shared with the user.
    :rtype: QuerySet[LLMHost]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> shared_llmhosts = get_cached_llmhosts_shared_with_user_profile(user_profile)
        >>> for bot in shared_llmhosts:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_llmhosts_shared_with_user_profile` - Invalidate the cache for shared LLMHosts of a user profile.
    """

    return _get_cached_llmhosts_shared_with_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_llmhosts_shared_with_user_profile(user_profile: UserProfile) -> None:
    _get_cached_llmhosts_shared_with_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_llmhosts_available_to_user_profile(user_profile_id) -> models.QuerySet[LLMHost]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = LLMHost.objects.with_read_permission_for(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching LLMHosts: %s",
        logger_prefix,
        logging.formatted_json(LLMHostSerializer(retval, many=True).data),
    )
    return retval


def get_cached_llmhosts_available_to_user_profile(user_profile: UserProfile) -> models.QuerySet[LLMHost]:
    """
    Retrieve the LLMHosts available to the given UserProfile, using caching to optimize performance.

    This function returns a queryset of LLMHost objects that are available to the specified user profile,
    which may include both owned and shared LLMHosts. The results are cached to reduce database queries
    and improve performance. If the cache is invalidated, the queryset is fetched from the database again
    and re-cached.

    :param user_profile: The user profile whose available LLMHosts should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the LLMHost objects available to the user.
    :rtype: QuerySet[LLMHost]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> available_llmhosts = get_cached_llmhosts_available_to_user_profile(user_profile)
        >>> for bot in available_llmhosts:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_llmhosts_available_to_user_profile` - Invalidate the cache for available LLMHosts of a user profile.
    """

    return _get_cached_llmhosts_available_to_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_llmhosts_available_to_user_profile(user_profile: UserProfile) -> None:
    _get_cached_llmhosts_available_to_user_profile.invalidate(user_profile.id)  # type: ignore


def invalidate_all_cached_llmhosts_for_user_profile(user_profile: UserProfile) -> None:
    """
    Invalidate all cached LLMHost querysets related to the given UserProfile.

    This function invalidates the caches for all LLMHost querysets that are related to the specified user profile,
    including owned, shared, and available LLMHosts. This is useful when a change occurs that may
    affect any of these querysets, ensuring that subsequent calls will fetch fresh data from the database.

    :param user_profile: The user profile for which to invalidate cached LLMHost querysets.
    :type user_profile: UserProfile
    :returns: None
    :rtype: None

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> invalidate_all_cached_llmhosts_for_user_profile(user_profile)

    .. seealso::

        - :func:`invalidate_cached_llmhosts_owned_by_user_profile` - Invalidate the cache for owned LLMHosts of a user profile.
        - :func:`invalidate_cached_llmhosts_shared_with_user_profile` - Invalidate the cache for shared LLMHosts of a user profile.
        - :func:`invalidate_cached_llmhosts_available_to_user_profile` - Invalidate the cache for available LLMHosts of a user profile.
    """
    invalidate_cached_llmhosts_owned_by_user_profile(user_profile=user_profile)
    invalidate_cached_llmhosts_shared_with_user_profile(user_profile=user_profile)
    invalidate_cached_llmhosts_available_to_user_profile(user_profile=user_profile)
