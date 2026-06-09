# pylint: disable=W0613,W0212
"""
Cache management utilities for AuthToken objects.

This module provides functions for efficient type-annotated retrieval and
caching of AuthToken querysets. It includes utilities to:

- Retrieve and cache AuthTokens owned by a user profile
- Retrieve and cache AuthTokens shared with a user profile
- Retrieve and cache AuthTokens available to a user profile (owned or shared)
- Invalidate caches for owned, shared, and available AuthTokens
- Invalidate all AuthToken-related caches for a user profile

Functions:

    - get_cached_authtokens_owned_by_user_profile(user_profile)
    - invalidate_cached_authtokens_owned_by_user_profile(user_profile)
    - get_cached_authtokens_shared_with_user_profile(user_profile)
    - invalidate_cached_authtokens_shared_with_user_profile(user_profile)
    - get_cached_authtokens_available_to_user_profile(user_profile)
    - invalidate_cached_authtokens_available_to_user_profile(user_profile)
    - invalidate_all_cached_authtokens_for_user_profile(user_profile)

Dependencies:

    - Django ORM
    - smarter.lib.cache.cache_results
    - smarter.apps.account.models.user_profile.UserProfile
    - smarter.apps.authtoken.models.AuthToken
    - smarter.apps.authtoken.serializers.AuthTokenSerializer

"""

from django.db import models

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import SmarterAuthToken as AuthToken
from .serializers.authtoken import SmarterAuthTokenSerializer as AuthTokenSerializer

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.SECRET_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@cache_results()
def _get_cached_authtokens_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[AuthToken]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = AuthToken.objects.owned_by(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching AuthTokens owned by user: %s",
        logger_prefix,
        logging.formatted_json(AuthTokenSerializer(retval, many=True).data),
    )
    return retval


def get_cached_authtokens_owned_by_user_profile(user_profile: UserProfile) -> models.QuerySet[AuthToken]:
    """
    Retrieve the AuthTokens owned by the given UserProfile, using caching to optimize performance.

    This function returns a queryset of AuthToken objects that are owned by the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose owned AuthTokens should be retrieved.
    :type user_profile: UserProfile

    :returns: A Django queryset containing the AuthToken objects owned by the user.
    :rtype: QuerySet[AuthToken]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> authtokens = get_cached_authtokens_owned_by_user_profile(user_profile)
        >>> for bot in authtokens:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_authtokens_owned_by_user_profile` - Invalidate the cache for owned AuthTokens of a user profile.
    """

    return _get_cached_authtokens_owned_by_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_authtokens_owned_by_user_profile(user_profile: UserProfile) -> None:
    _get_cached_authtokens_owned_by_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_authtokens_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[AuthToken]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = AuthToken.objects.shared_with(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching AuthTokens shared with user: %s",
        logger_prefix,
        logging.formatted_json(AuthTokenSerializer(retval, many=True).data),
    )
    return retval


def get_cached_authtokens_shared_with_user_profile(user_profile: UserProfile) -> models.QuerySet[AuthToken]:
    """
    Retrieve the AuthTokens shared with the given UserProfile, using caching to optimize performance.

    This function returns a queryset of AuthToken objects that are shared with the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose shared AuthTokens should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the AuthToken objects shared with the user.
    :rtype: QuerySet[AuthToken]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> shared_authtokens = get_cached_authtokens_shared_with_user_profile(user_profile)
        >>> for bot in shared_authtokens:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_authtokens_shared_with_user_profile` - Invalidate the cache for shared AuthTokens of a user profile.
    """

    return _get_cached_authtokens_shared_with_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_authtokens_shared_with_user_profile(user_profile: UserProfile) -> None:
    _get_cached_authtokens_shared_with_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_authtokens_available_to_user_profile(user_profile_id) -> models.QuerySet[AuthToken]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = AuthToken.objects.with_read_permission_for(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching and caching AuthTokens available to user: %s",
        logger_prefix,
        logging.formatted_json(AuthTokenSerializer(retval, many=True).data),
    )
    return retval


def get_cached_authtokens_available_to_user_profile(user_profile: UserProfile) -> models.QuerySet[AuthToken]:
    """
    Retrieve the AuthTokens available to the given UserProfile, using caching to optimize performance.

    This function returns a queryset of AuthToken objects that are available to the specified user profile,
    which may include both owned and shared AuthTokens. The results are cached to reduce database queries
    and improve performance. If the cache is invalidated, the queryset is fetched from the database again
    and re-cached.

    :param user_profile: The user profile whose available AuthTokens should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the AuthToken objects available to the user.
    :rtype: QuerySet[AuthToken]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> available_authtokens = get_cached_authtokens_available_to_user_profile(user_profile)
        >>> for bot in available_authtokens:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_authtokens_available_to_user_profile` - Invalidate the cache for available AuthTokens of a user profile.
    """

    return _get_cached_authtokens_available_to_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_authtokens_available_to_user_profile(user_profile: UserProfile) -> None:
    _get_cached_authtokens_available_to_user_profile.invalidate(user_profile.id)  # type: ignore


def invalidate_all_cached_authtokens_for_user_profile(user_profile: UserProfile) -> None:
    """
    Invalidate all cached AuthToken querysets related to the given UserProfile.

    This function invalidates the caches for all AuthToken querysets that are related to the specified user profile,
    including owned, shared, and available AuthTokens. This is useful when a change occurs that may
    affect any of these querysets, ensuring that subsequent calls will fetch fresh data from the database.

    :param user_profile: The user profile for which to invalidate cached AuthToken querysets.
    :type user_profile: UserProfile
    :returns: None
    :rtype: None

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> invalidate_all_cached_authtokens_for_user_profile(user_profile)

    .. seealso::

        - :func:`invalidate_cached_authtokens_owned_by_user_profile` - Invalidate the cache for owned AuthTokens of a user profile.
        - :func:`invalidate_cached_authtokens_shared_with_user_profile` - Invalidate the cache for shared AuthTokens of a user profile.
        - :func:`invalidate_cached_authtokens_available_to_user_profile` - Invalidate the cache for available AuthTokens of a user profile.
    """
    invalidate_cached_authtokens_owned_by_user_profile(user_profile=user_profile)
    invalidate_cached_authtokens_shared_with_user_profile(user_profile=user_profile)
    invalidate_cached_authtokens_available_to_user_profile(user_profile=user_profile)
