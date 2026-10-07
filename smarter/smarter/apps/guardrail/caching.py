# pylint: disable=W0613,W0212
"""
Cache management utilities for Guardrail objects.

This module provides functions for efficient type-annotated retrieval and
caching of Guardrail querysets. It includes utilities to:

- Retrieve and cache Guardrails owned by a user profile
- Retrieve and cache Guardrails shared with a user profile
- Retrieve and cache Guardrails available to a user profile (owned or shared)
- Invalidate caches for owned, shared, and available Guardrails
- Invalidate all Guardrail-related caches for a user profile

Functions:

    - get_cached_guardrails_owned_by_user_profile(user_profile)
    - invalidate_cached_guardrails_owned_by_user_profile(user_profile)
    - get_cached_guardrails_shared_with_user_profile(user_profile)
    - invalidate_cached_guardrails_shared_with_user_profile(user_profile)
    - get_cached_guardrails_available_to_user_profile(user_profile)
    - invalidate_cached_guardrails_available_to_user_profile(user_profile)
    - invalidate_all_cached_guardrails_for_user_profile(user_profile)

Dependencies:

    - Django ORM
    - smarter.lib.cache.cache_results
    - smarter.apps.account.models.user_profile.UserProfile
    - smarter.apps.guardrail.models.Guardrail
    - smarter.apps.guardrail.serializers.GuardrailSerializer
"""

from django.db import models

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import Guardrail
from .serializers import GuardrailSerializer

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@cache_results()
def _get_cached_guardrails_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[Guardrail]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Guardrail.objects.owned_by(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching Guardrails: %s",
        logger_prefix,
        logging.formatted_json(GuardrailSerializer(retval, many=True).data),
    )
    return retval


def get_cached_guardrails_owned_by_user_profile(user_profile: UserProfile) -> models.QuerySet[Guardrail]:
    """
    Retrieve the Guardrails owned by the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Guardrail objects that are owned by the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose owned Guardrails should be retrieved.
    :type user_profile: UserProfile

    :returns: A Django queryset containing the Guardrail objects owned by the user.
    :rtype: QuerySet[Guardrail]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> guardrails = get_cached_guardrails_owned_by_user_profile(user_profile)
        >>> for bot in guardrails:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_guardrails_owned_by_user_profile` - Invalidate the cache for owned Guardrails of a user profile.
    """

    return _get_cached_guardrails_owned_by_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_guardrails_owned_by_user_profile(user_profile: UserProfile) -> None:
    _get_cached_guardrails_owned_by_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_guardrails_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[Guardrail]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Guardrail.objects.shared_with(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching Guardrails: %s",
        logger_prefix,
        logging.formatted_json(GuardrailSerializer(retval, many=True).data),
    )
    return retval


def get_cached_guardrails_shared_with_user_profile(user_profile: UserProfile) -> models.QuerySet[Guardrail]:
    """
    Retrieve the Guardrails shared with the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Guardrail objects that are shared with the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose shared Guardrails should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the Guardrail objects shared with the user.
    :rtype: QuerySet[Guardrail]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> shared_guardrails = get_cached_guardrails_shared_with_user_profile(user_profile)
        >>> for bot in shared_guardrails:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_guardrails_shared_with_user_profile` - Invalidate the cache for shared Guardrails of a user profile.
    """

    return _get_cached_guardrails_shared_with_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_guardrails_shared_with_user_profile(user_profile: UserProfile) -> None:
    _get_cached_guardrails_shared_with_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_guardrails_available_to_user_profile(user_profile_id) -> models.QuerySet[Guardrail]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = Guardrail.objects.with_read_permission_for(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching Guardrails: %s",
        logger_prefix,
        logging.formatted_json(GuardrailSerializer(retval, many=True).data),
    )
    return retval


def get_cached_guardrails_available_to_user_profile(user_profile: UserProfile) -> models.QuerySet[Guardrail]:
    """
    Retrieve the Guardrails available to the given UserProfile, using caching to optimize performance.

    This function returns a queryset of Guardrail objects that are available to the specified user profile,
    which may include both owned and shared Guardrails. The results are cached to reduce database queries
    and improve performance. If the cache is invalidated, the queryset is fetched from the database again
    and re-cached.

    :param user_profile: The user profile whose available Guardrails should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the Guardrail objects available to the user.
    :rtype: QuerySet[Guardrail]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> available_guardrails = get_cached_guardrails_available_to_user_profile(user_profile)
        >>> for bot in available_guardrails:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_guardrails_available_to_user_profile` - Invalidate the cache for available Guardrails of a user profile.
    """

    return _get_cached_guardrails_available_to_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_guardrails_available_to_user_profile(user_profile: UserProfile) -> None:
    _get_cached_guardrails_available_to_user_profile.invalidate(user_profile.id)  # type: ignore


def invalidate_all_cached_guardrails_for_user_profile(user_profile: UserProfile) -> None:
    """
    Invalidate all cached Guardrail querysets related to the given UserProfile.

    This function invalidates the caches for all Guardrail querysets that are related to the specified user profile,
    including owned, shared, and available Guardrails. This is useful when a change occurs that may
    affect any of these querysets, ensuring that subsequent calls will fetch fresh data from the database.

    :param user_profile: The user profile for which to invalidate cached Guardrail querysets.
    :type user_profile: UserProfile
    :returns: None
    :rtype: None

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> invalidate_all_cached_guardrails_for_user_profile(user_profile)

    .. seealso::

        - :func:`invalidate_cached_guardrails_owned_by_user_profile` - Invalidate the cache for owned Guardrails of a user profile.
        - :func:`invalidate_cached_guardrails_shared_with_user_profile` - Invalidate the cache for shared Guardrails of a user profile.
        - :func:`invalidate_cached_guardrails_available_to_user_profile` - Invalidate the cache for available Guardrails of a user profile.
    """
    invalidate_cached_guardrails_owned_by_user_profile(user_profile=user_profile)
    invalidate_cached_guardrails_shared_with_user_profile(user_profile=user_profile)
    invalidate_cached_guardrails_available_to_user_profile(user_profile=user_profile)
