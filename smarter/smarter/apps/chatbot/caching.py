# pylint: disable=W0613,W0212
"""
Cache management utilities for ChatBot objects.

This module provides functions for efficient type-annotated retrieval and
caching of ChatBot querysets. It includes utilities to:

- Retrieve and cache ChatBots owned by a user profile
- Retrieve and cache ChatBots shared with a user profile
- Retrieve and cache ChatBots available to a user profile (owned or shared)
- Invalidate caches for owned, shared, and available ChatBots
- Invalidate all ChatBot-related caches for a user profile

Functions:

    - get_cached_chatbots_owned_by_user_profile(user_profile)
    - invalidate_cached_chatbots_owned_by_user_profile(user_profile)
    - get_cached_chatbots_shared_with_user_profile(user_profile)
    - invalidate_cached_chatbots_shared_with_user_profile(user_profile)
    - get_cached_chatbots_available_to_user_profile(user_profile)
    - invalidate_cached_chatbots_available_to_user_profile(user_profile)
    - invalidate_all_cached_chatbots_for_user_profile(user_profile)

Dependencies:

    - Django ORM
    - smarter.lib.cache.cache_results
    - smarter.apps.account.models.user_profile.UserProfile
    - smarter.apps.chatbot.models.ChatBot
    - smarter.apps.chatbot.serializers.ChatBotSerializer

"""

from django.db import models

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import ChatBot
from .serializers import ChatBotSerializer

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.CHATBOT_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)
logger_prefix = logging.formatted_text(__name__)


@cache_results()
def _get_cached_chatbots_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[ChatBot]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = ChatBot.objects.owned_by(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching ChatBots: %s",
        logger_prefix,
        logging.formatted_json(ChatBotSerializer(retval, many=True).data),
    )
    return retval


def get_cached_chatbots_owned_by_user_profile(user_profile: UserProfile) -> models.QuerySet[ChatBot]:
    """
    Retrieve the ChatBots owned by the given UserProfile, using caching to optimize performance.

    This function returns a queryset of ChatBot objects that are owned by the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose owned ChatBots should be retrieved.
    :type user_profile: UserProfile

    :returns: A Django queryset containing the ChatBot objects owned by the user.
    :rtype: QuerySet[ChatBot]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> chatbots = get_cached_chatbots_owned_by_user_profile(user_profile)
        >>> for bot in chatbots:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_chatbots_owned_by_user_profile` - Invalidate the cache for owned ChatBots of a user profile.
    """

    return _get_cached_chatbots_owned_by_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_chatbots_owned_by_user_profile(user_profile: UserProfile) -> None:
    _get_cached_chatbots_owned_by_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_chatbots_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[ChatBot]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = ChatBot.objects.shared_with(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching ChatBots: %s",
        logger_prefix,
        logging.formatted_json(ChatBotSerializer(retval, many=True).data),
    )
    return retval


def get_cached_chatbots_shared_with_user_profile(user_profile: UserProfile) -> models.QuerySet[ChatBot]:
    """
    Retrieve the ChatBots shared with the given UserProfile, using caching to optimize performance.

    This function returns a queryset of ChatBot objects that are shared with the specified user profile.
    The results are cached to reduce database queries and improve performance. If the cache is invalidated,
    the queryset is fetched from the database again and re-cached.

    :param user_profile: The user profile whose shared ChatBots should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the ChatBot objects shared with the user.
    :rtype: QuerySet[ChatBot]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> shared_chatbots = get_cached_chatbots_shared_with_user_profile(user_profile)
        >>> for bot in shared_chatbots:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_chatbots_shared_with_user_profile` - Invalidate the cache for shared ChatBots of a user profile.
    """

    return _get_cached_chatbots_shared_with_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_chatbots_shared_with_user_profile(user_profile: UserProfile) -> None:
    _get_cached_chatbots_shared_with_user_profile.invalidate(user_profile.id)  # type: ignore


@cache_results()
def _get_cached_chatbots_available_to_user_profile(user_profile_id) -> models.QuerySet[ChatBot]:
    user_profile = UserProfile.objects.get(id=user_profile_id)  # type: ignore
    retval = ChatBot.objects.with_read_permission_for(user_profile.user)  # type: ignore
    logger.debug(
        "%s.post() Fetching ChatBots: %s",
        logger_prefix,
        logging.formatted_json(ChatBotSerializer(retval, many=True).data),
    )
    return retval


def get_cached_chatbots_available_to_user_profile(user_profile: UserProfile) -> models.QuerySet[ChatBot]:
    """
    Retrieve the ChatBots available to the given UserProfile, using caching to optimize performance.

    This function returns a queryset of ChatBot objects that are available to the specified user profile,
    which may include both owned and shared ChatBots. The results are cached to reduce database queries
    and improve performance. If the cache is invalidated, the queryset is fetched from the database again
    and re-cached.

    :param user_profile: The user profile whose available ChatBots should be retrieved.
    :type user_profile: UserProfile
    :returns: A Django queryset containing the ChatBot objects available to the user.
    :rtype: QuerySet[ChatBot]

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> available_chatbots = get_cached_chatbots_available_to_user_profile(user_profile)
        >>> for bot in available_chatbots:
        ...     print(bot.name)

    .. seealso::

        - :func:`invalidate_cached_chatbots_available_to_user_profile` - Invalidate the cache for available ChatBots of a user profile.
    """

    return _get_cached_chatbots_available_to_user_profile(user_profile.id)  # type: ignore


def invalidate_cached_chatbots_available_to_user_profile(user_profile: UserProfile) -> None:
    _get_cached_chatbots_available_to_user_profile.invalidate(user_profile.id)  # type: ignore


def invalidate_all_cached_chatbots_for_user_profile(user_profile: UserProfile) -> None:
    """
    Invalidate all cached ChatBot querysets related to the given UserProfile.

    This function invalidates the caches for all ChatBot querysets that are related to the specified user profile,
    including owned, shared, and available ChatBots. This is useful when a change occurs that may
    affect any of these querysets, ensuring that subsequent calls will fetch fresh data from the database.

    :param user_profile: The user profile for which to invalidate cached ChatBot querysets.
    :type user_profile: UserProfile
    :returns: None
    :rtype: None

    .. code-block:: python

        >>> user_profile = UserProfile.objects.get(pk=1)
        >>> invalidate_all_cached_chatbots_for_user_profile(user_profile)

    .. seealso::

        - :func:`invalidate_cached_chatbots_owned_by_user_profile` - Invalidate the cache for owned ChatBots of a user profile.
        - :func:`invalidate_cached_chatbots_shared_with_user_profile` - Invalidate the cache for shared ChatBots of a user profile.
        - :func:`invalidate_cached_chatbots_available_to_user_profile` - Invalidate the cache for available ChatBots of a user profile.
    """
    invalidate_cached_chatbots_owned_by_user_profile(user_profile=user_profile)
    invalidate_cached_chatbots_shared_with_user_profile(user_profile=user_profile)
    invalidate_cached_chatbots_available_to_user_profile(user_profile=user_profile)
