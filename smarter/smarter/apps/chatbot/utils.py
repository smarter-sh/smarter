"""
Chatbot utility functions.
"""

from functools import lru_cache
from logging import getLogger
from typing import Optional

from django.db.models import QuerySet

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    get_cached_user_profile,
    smarter_cached_objects,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import ChatBot, ChatBotHelper

logger = getLogger(__name__)
logger_prefix = formatted_text(f"{__name__}")

LRU_CACHE_MAX_SIZE = 128


@cache_results()
def get_cached_chatbot(
    chatbot_name: Optional[str] = None, chatbot_account: Optional[Account] = None, chatbot_id: Optional[int] = None
) -> Optional[ChatBot]:
    """
    Returns the chatbot for the given chatbot_id or chatbot_number.
    """

    @lru_cache(maxsize=LRU_CACHE_MAX_SIZE)
    def _in_memory_chatbot_by_id(chatbot_id):
        """
        In-memory cache for chatbot objects by ID.
        """
        chatbot = ChatBot.objects.get(id=chatbot_id)
        if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger.debug("_in_memory_chatbot_by_id() retrieving and caching chatbot %s", chatbot)
        return chatbot

    # pylint: disable=W0613
    @lru_cache(maxsize=LRU_CACHE_MAX_SIZE)
    def _in_memory_chatbot_by_name(chatbot_name, chatbot_account_number):
        """
        In-memory cache for chatbot objects by chatbot number.
        """
        chatbot = ChatBot.objects.get(name=chatbot_name, account=chatbot_account)
        if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger.debug("_in_memory_chatbot_by_number() retrieving and caching chatbot %s", chatbot)
        return chatbot

    if chatbot_id:
        return _in_memory_chatbot_by_id(chatbot_id=chatbot_id)

    account_number = chatbot_account.account_number if chatbot_account else None
    if chatbot_name and account_number:
        return _in_memory_chatbot_by_name(chatbot_name=chatbot_name, chatbot_account_number=account_number)


@cache_results()
def get_cached_chatbots_for_user_profile(user_profile_id: int) -> list[ChatBotHelper]:
    """
    Returns a list of chatbots for the given user profile.
    """

    def was_already_added(chatbot_helper: ChatBotHelper) -> bool:
        if not chatbot_helper.chatbot:
            logger.error("%s.dispatch() - chatbot_helper.chatbot is None. This is a bug.", logger_prefix)
            return False
        for b in chatbot_helpers:
            if b.chatbot and b.chatbot.id == chatbot_helper.chatbot.id:  # type: ignore[union-attr]
                return True
        return False

    def get_chatbots_for_account() -> QuerySet:
        user_chatbots = ChatBot.objects.filter(user_profile=user_profile).order_by("name")
        admin_chatbots = ChatBot.objects.filter(user_profile=admin_user_profile).order_by("name")
        smarter_chatbots = ChatBot.objects.filter(
            user_profile=smarter_cached_objects.smarter_admin_user_profile
        ).order_by("name")
        combined_chatbots = user_chatbots | admin_chatbots | smarter_chatbots
        combined_chatbots = combined_chatbots.distinct().order_by("name")
        return combined_chatbots

    logger.debug(
        "%s.get_cached_chatbots_for_user_profile() - Getting chatbots for user_profile_id %s",
        logger_prefix,
        user_profile_id,
    )

    chatbot_helpers = []
    user_profile = UserProfile.objects.get(id=user_profile_id)
    admin_user = get_cached_admin_user_for_account(account=user_profile.account)
    if admin_user:
        admin_user_profile = get_cached_user_profile(user=admin_user)
    else:
        logger.error(
            "%s.get_cached_chatbots_for_user_profile() - No admin user found for account %s",
            logger_prefix,
            user_profile.account,
        )
        return []

    chatbots = get_chatbots_for_account()
    logger.debug(
        "%s.get_cached_chatbots_for_user_profile() - Retrieved %d chatbots for user_profile_id %s",
        logger_prefix,
        len(chatbots),
        user_profile_id,
    )

    i = 0
    for chatbot in chatbots:
        i += 1
        logger.debug(
            "%s.get_cached_chatbots_for_user_profile() - Processing chatbot %s %s for user_profile_id %s",
            logger_prefix,
            i,
            chatbot,
            user_profile_id,
        )
        chatbot_helper = ChatBotHelper(
            request=None,
            chatbot=chatbot,
            user=user_profile.user,
            user_profile=user_profile,
            account=user_profile.account,
        )
        if not was_already_added(chatbot_helper):
            chatbot_helpers.append(chatbot_helper)

    logger.debug(
        "%s.get_cached_chatbots_for_user_profile() - Retrieved %d chatbots for user_profile %s",
        logger_prefix,
        len(chatbot_helpers),
        user_profile,
    )

    try:
        pass

    # pylint: disable=broad-except
    except Exception as e:
        logger.error(
            "%s.get_cached_chatbots_for_user_profile() - Exception occurred while getting chatbots for user_profile %s. Exception: %s",
            logger_prefix,
            user_profile,
            e,
        )
        return []

    return chatbot_helpers
