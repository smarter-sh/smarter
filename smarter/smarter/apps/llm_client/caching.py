# pylint: disable=W0613,W0212
"""
Cache management utilities for LLMClient objects.

This module provides functions for efficient type-annotated retrieval and
caching of LLMClient querysets. It includes utilities to:

- Retrieve and cache LLMClients owned by a user profile
- Retrieve and cache LLMClients shared with a user profile
- Retrieve and cache LLMClients available to a user profile (owned or shared)
- Invalidate caches for owned, shared, and available LLMClients
- Invalidate all LLMClient-related caches for a user profile

Functions:

    - get_cached_llm_clients_owned_by_user_profile(user_profile)
    - invalidate_cached_llm_clients_owned_by_user_profile(user_profile)
    - get_cached_llm_clients_shared_with_user_profile(user_profile)
    - invalidate_cached_llm_clients_shared_with_user_profile(user_profile)
    - get_cached_llm_clients_available_to_user_profile(user_profile)
    - invalidate_cached_llm_clients_available_to_user_profile(user_profile)
    - invalidate_all_cached_llm_clients_for_user_profile(user_profile)

Dependencies:

    - Django ORM
    - smarter.lib.cache.cache_results
    - smarter.apps.account.models.user_profile.UserProfile
    - smarter.apps.llm_client.models.LLMClient
    - smarter.apps.llm_client.serializers.LLMClientSerializer
"""

from django.db import models

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import LLMClient
from .serializers import LLMClientSerializer

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@cache_results()
def _get_cached_llm_clients_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[LLMClient]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = LLMClient.objects.owned_by(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching LLMClients: %s",
        logger_prefix,
        logging.formatted_json(LLMClientSerializer(retval, many=True).data),
    )
    return retval


def get_cached_llm_clients_owned_by_user_profile(user_profile: UserProfile) -> models.QuerySet[LLMClient]:
    """
    Retrieve the LLMClients owned by the given UserProfile, using caching to optimize performance.

    This function returns a queryset of LLMClient objects that are owned by the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose owned LLMClients should be retrieved.
    :type user_profile: UserProfile

    :returns: A Django queryset containing the LLMClient objects owned by the user.
    :rtype: QuerySet[LLMClient]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> llm_clients = get_cached_llm_clients_owned_by_user_profile(user_profile)
        >>> for bot in llm_clients:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_llm_clients_owned_by_user_profile` - Invalidate the cache for owned LLMClients of a user profile.
    """

    return _get_cached_llm_clients_owned_by_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_llm_clients_owned_by_user_profile(user_profile: UserProfile) -> None:
    _get_cached_llm_clients_owned_by_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_llm_clients_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[LLMClient]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = LLMClient.objects.shared_with(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching LLMClients: %s",
        logger_prefix,
        logging.formatted_json(LLMClientSerializer(retval, many=True).data),
    )
    return retval


def get_cached_llm_clients_shared_with_user_profile(user_profile: UserProfile) -> models.QuerySet[LLMClient]:
    """
    Retrieve the LLMClients shared with the given UserProfile, using caching to optimize performance.

    This function returns a queryset of LLMClient objects that are shared with the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose shared LLMClients should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the LLMClient objects shared with the user.
    :rtype: QuerySet[LLMClient]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> shared_llm_clients = get_cached_llm_clients_shared_with_user_profile(user_profile)
        >>> for bot in shared_llm_clients:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_llm_clients_shared_with_user_profile` - Invalidate the cache for shared LLMClients of a user profile.
    """

    return _get_cached_llm_clients_shared_with_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_llm_clients_shared_with_user_profile(user_profile: UserProfile) -> None:
    _get_cached_llm_clients_shared_with_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_llm_clients_available_to_user_profile(user_profile_id) -> models.QuerySet[LLMClient]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = LLMClient.objects.with_read_permission_for(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching LLMClients: %s",
        logger_prefix,
        logging.formatted_json(LLMClientSerializer(retval, many=True).data),
    )
    return retval


def get_cached_llm_clients_available_to_user_profile(user_profile: UserProfile) -> models.QuerySet[LLMClient]:
    """
    Retrieve the LLMClients available to the given UserProfile, using caching to optimize performance.

    This function returns a queryset of LLMClient objects that are available to the specified user profile,
    which may include both owned and shared LLMClients. The results are cached to reduce database queries
    and improve performance. If the cache is invalidated, the queryset is fetched from the database again
    and re-cached.

    :param user_profile: The user profile whose available LLMClients should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the LLMClient objects available to the user.
    :rtype: QuerySet[LLMClient]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> available_llm_clients = get_cached_llm_clients_available_to_user_profile(user_profile)
        >>> for bot in available_llm_clients:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_llm_clients_available_to_user_profile` - Invalidate the cache for available LLMClients of a user profile.
    """

    return _get_cached_llm_clients_available_to_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_llm_clients_available_to_user_profile(user_profile: UserProfile) -> None:
    _get_cached_llm_clients_available_to_user_profile.invalidate(user_profile.id)  # type: ignore


def invalidate_all_cached_llm_clients_for_user_profile(user_profile: UserProfile) -> None:
    """
    Invalidate all cached LLMClient querysets related to the given UserProfile.

    This function invalidates the caches for all LLMClient querysets that are related to the specified user profile,
    including owned, shared, and available LLMClients. This is useful when a change occurs that may
    affect any of these querysets, ensuring that subsequent calls will fetch fresh data from the database.

    :param user_profile: The user profile for which to invalidate cached LLMClient querysets.
    :type user_profile: UserProfile
    :returns: None
    :rtype: None

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> invalidate_all_cached_llm_clients_for_user_profile(user_profile)

    .. seealso::

        - :func:`invalidate_cached_llm_clients_owned_by_user_profile` - Invalidate the cache for owned LLMClients of a user profile.
        - :func:`invalidate_cached_llm_clients_shared_with_user_profile` - Invalidate the cache for shared LLMClients of a user profile.
        - :func:`invalidate_cached_llm_clients_available_to_user_profile` - Invalidate the cache for available LLMClients of a user profile.
    """
    invalidate_cached_llm_clients_owned_by_user_profile(user_profile=user_profile)
    invalidate_cached_llm_clients_shared_with_user_profile(user_profile=user_profile)
    invalidate_cached_llm_clients_available_to_user_profile(user_profile=user_profile)
