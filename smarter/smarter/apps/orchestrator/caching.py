# pylint: disable=W0613,W0212
"""
Cache management utilities for Orchestrator objects.

This module provides functions for efficient type-annotated retrieval and
caching of Orchestrator querysets. It includes utilities to:

- Retrieve and cache Orchestrators owned by a user profile
- Retrieve and cache Orchestrators shared with a user profile
- Retrieve and cache Orchestrators available to a user profile (owned or shared)
- Invalidate caches for owned, shared, and available Orchestrators
- Invalidate all Orchestrator-related caches for a user profile

Functions:

    - get_cached_orchestrators_owned_by_user_profile(user_profile)
    - invalidate_cached_orchestrators_owned_by_user_profile(user_profile)
    - get_cached_orchestrators_shared_with_user_profile(user_profile)
    - invalidate_cached_orchestrators_shared_with_user_profile(user_profile)
    - get_cached_orchestrators_available_to_user_profile(user_profile)
    - invalidate_cached_orchestrators_available_to_user_profile(user_profile)
    - invalidate_all_cached_orchestrators_for_user_profile(user_profile)

Dependencies:

    - Django ORM
    - smarter.lib.cache.cache_results
    - smarter.apps.account.models.user_profile.UserProfile
    - smarter.apps.orchestrator.models.Orchestrator
    - smarter.apps.orchestrator.serializers.OrchestratorSerializer
"""

from django.db import models

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Orchestrator
from .serializers import OrchestratorSerializer

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@cache_results()
def _get_cached_orchestrators_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[Orchestrator]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Orchestrator.objects.owned_by(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching Orchestrators: %s",
        logger_prefix,
        logging.formatted_json(OrchestratorSerializer(retval, many=True).data),
    )
    return retval


def get_cached_orchestrators_owned_by_user_profile(user_profile: UserProfile) -> models.QuerySet[Orchestrator]:
    """
    Retrieve the Orchestrators owned by the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Orchestrator objects that are owned by the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose owned Orchestrators should be retrieved.
    :type user_profile: UserProfile

    :returns: A Django queryset containing the Orchestrator objects owned by the user.
    :rtype: QuerySet[Orchestrator]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> orchestrators = get_cached_orchestrators_owned_by_user_profile(user_profile)
        >>> for bot in orchestrators:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_orchestrators_owned_by_user_profile` - Invalidate the cache for owned Orchestrators of a user profile.
    """

    return _get_cached_orchestrators_owned_by_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_orchestrators_owned_by_user_profile(user_profile: UserProfile) -> None:
    _get_cached_orchestrators_owned_by_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_orchestrators_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[Orchestrator]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Orchestrator.objects.shared_with(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching Orchestrators: %s",
        logger_prefix,
        logging.formatted_json(OrchestratorSerializer(retval, many=True).data),
    )
    return retval


def get_cached_orchestrators_shared_with_user_profile(user_profile: UserProfile) -> models.QuerySet[Orchestrator]:
    """
    Retrieve the Orchestrators shared with the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Orchestrator objects that are shared with the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose shared Orchestrators should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the Orchestrator objects shared with the user.
    :rtype: QuerySet[Orchestrator]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> shared_orchestrators = get_cached_orchestrators_shared_with_user_profile(user_profile)
        >>> for bot in shared_orchestrators:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_orchestrators_shared_with_user_profile` - Invalidate the cache for shared Orchestrators of a user profile.
    """

    return _get_cached_orchestrators_shared_with_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_orchestrators_shared_with_user_profile(user_profile: UserProfile) -> None:
    _get_cached_orchestrators_shared_with_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_orchestrators_available_to_user_profile(user_profile_id) -> models.QuerySet[Orchestrator]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Orchestrator.objects.with_read_permission_for(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching Orchestrators: %s",
        logger_prefix,
        logging.formatted_json(OrchestratorSerializer(retval, many=True).data),
    )
    return retval


def get_cached_orchestrators_available_to_user_profile(user_profile: UserProfile) -> models.QuerySet[Orchestrator]:
    """
    Retrieve the Orchestrators available to the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Orchestrator objects that are available to the specified user profile,
    which may include both owned and shared Orchestrators. The results are cached to reduce database queries
    and improve performance. If the cache is invalidated, the queryset is fetched from the database again
    and re-cached.

    :param user_profile: The user profile whose available Orchestrators should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the Orchestrator objects available to the user.
    :rtype: QuerySet[Orchestrator]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> available_orchestrators = get_cached_orchestrators_available_to_user_profile(user_profile)
        >>> for bot in available_orchestrators:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_orchestrators_available_to_user_profile` - Invalidate the cache for available Orchestrators of a user profile.
    """

    return _get_cached_orchestrators_available_to_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_orchestrators_available_to_user_profile(user_profile: UserProfile) -> None:
    _get_cached_orchestrators_available_to_user_profile.invalidate(user_profile.id)  # type: ignore


def invalidate_all_cached_orchestrators_for_user_profile(user_profile: UserProfile) -> None:
    """
    Invalidate all cached Orchestrator querysets related to the given UserProfile.

    This function invalidates the caches for all Orchestrator querysets that are related to the specified user profile,
    including owned, shared, and available Orchestrators. This is useful when a change occurs that may
    affect any of these querysets, ensuring that subsequent calls will fetch fresh data from the database.

    :param user_profile: The user profile for which to invalidate cached Orchestrator querysets.
    :type user_profile: UserProfile
    :returns: None
    :rtype: None

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> invalidate_all_cached_orchestrators_for_user_profile(user_profile)

    .. seealso::

        - :func:`invalidate_cached_orchestrators_owned_by_user_profile` - Invalidate the cache for owned Orchestrators of a user profile.
        - :func:`invalidate_cached_orchestrators_shared_with_user_profile` - Invalidate the cache for shared Orchestrators of a user profile.
        - :func:`invalidate_cached_orchestrators_available_to_user_profile` - Invalidate the cache for available Orchestrators of a user profile.
    """
    invalidate_cached_orchestrators_owned_by_user_profile(user_profile=user_profile)
    invalidate_cached_orchestrators_shared_with_user_profile(user_profile=user_profile)
    invalidate_cached_orchestrators_available_to_user_profile(user_profile=user_profile)
