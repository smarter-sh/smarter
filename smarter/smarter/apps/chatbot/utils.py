# pylint: disable=W0613
"""
Utility functions for ChatBot-related operations.
"""

from django.db import models

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results

from .models import ChatBot
from .serializers import ChatBotSerializer

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)


def get_cached_chatbots_owned_by_user_profile(
    user_profile: UserProfile, invalidate_cache: bool = False
) -> models.QuerySet[ChatBot]:

    user_profile_id = user_profile.id  # type: ignore

    @cache_results()
    def _get_cached_chatbots_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[ChatBot]:
        logger.debug(
            "%s.post() Fetching ChatBots owned by %s",
            logger_prefix,
            user_profile,
        )
        retval = ChatBot.objects.owned_by(user_profile.user)  # type: ignore
        logger.debug(
            "%s.post() Fetching ChatBots owned by %s: %s",
            logger_prefix,
            user_profile,
            logging.formatted_json(ChatBotSerializer(retval, many=True).data),
        )
        return retval

    if invalidate_cache:
        logger.debug(
            "%s.post() Invalidating cache for ChatBots owned by %s",
            logger_prefix,
            user_profile,
        )
        _get_cached_chatbots_owned_by_user_profile.invalidate(user_profile_id)
    return _get_cached_chatbots_owned_by_user_profile(user_profile_id)


def get_cached_chatbots_shared_with_user_profile(
    user_profile: UserProfile, invalidate_cache: bool = False
) -> models.QuerySet[ChatBot]:

    user_profile_id = user_profile.id  # type: ignore

    @cache_results()
    def _get_cached_chatbots_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[ChatBot]:
        logger.debug(
            "%s.post() Fetching ChatBots shared with %s",
            logger_prefix,
            user_profile,
        )
        retval = ChatBot.objects.shared_with(user_profile.user)  # type: ignore
        logger.debug(
            "%s.post() Fetching ChatBots shared with %s: %s",
            logger_prefix,
            user_profile,
            logging.formatted_json(ChatBotSerializer(retval, many=True).data),
        )
        return retval

    if invalidate_cache:
        logger.debug(
            "%s.post() Invalidating cache for ChatBots shared with %s",
            logger_prefix,
            user_profile,
        )
        _get_cached_chatbots_shared_with_user_profile.invalidate(user_profile_id)
    return _get_cached_chatbots_shared_with_user_profile(user_profile_id)


def get_cached_chatbots_available_to_user_profile(
    user_profile: UserProfile, invalidate_cache: bool = False
) -> models.QuerySet[ChatBot]:

    user_profile_id = user_profile.id  # type: ignore

    @cache_results()
    def _get_cached_chatbots_available_to_user_profile(user_profile_id) -> models.QuerySet[ChatBot]:
        logger.debug(
            "%s.post() Fetching ChatBots available to %s",
            logger_prefix,
            user_profile,
        )
        retval = ChatBot.objects.with_read_permission_for(user_profile.user)  # type: ignore
        logger.debug(
            "%s.post() Fetching ChatBots available to %s: %s",
            logger_prefix,
            user_profile,
            logging.formatted_json(ChatBotSerializer(retval, many=True).data),
        )
        return retval

    if invalidate_cache:
        logger.debug(
            "%s.post() Invalidating cache for ChatBots available to %s",
            logger_prefix,
            user_profile,
        )
        _get_cached_chatbots_available_to_user_profile.invalidate(user_profile_id)
    return _get_cached_chatbots_available_to_user_profile(user_profile_id)
