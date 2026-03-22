"""
Chatbot utility functions.
"""

from logging import getLogger

from django.db.models import QuerySet

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    get_cached_user_profile,
    smarter_cached_objects,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.cache import cache_results

from .models import ChatBot, ChatBotHelper

logger = getLogger(__name__)
logger_prefix = formatted_text(f"{__name__}")

LRU_CACHE_MAX_SIZE = 128


@cache_results(timeout=60)
def get_cached_chatbots_for_user_profile(user_profile_id: int) -> list[ChatBotHelper]:
    """
    Returns a list of chatbots for the given user profile.
    """
    try:

        def was_already_added(chatbot_helper: ChatBotHelper) -> bool:
            if not chatbot_helper.chatbot:
                logger.error("%s.dispatch() - chatbot_helper.chatbot is None. This is a bug.", logger_prefix)
                return False
            for b in chatbot_helpers:
                if b.chatbot and b.chatbot.id == chatbot_helper.chatbot.id:  # type: ignore[union-attr]
                    return True
            return False

        def get_chatbots_for_account() -> QuerySet:

            user_chatbots = ChatBot.get_cached_models(user_profile=user_profile)
            admin_chatbots = ChatBot.get_cached_models(user_profile=admin_user_profile)  # type: ignore[union-attr]
            smarter_chatbots = ChatBot.get_cached_models(
                user_profile=smarter_cached_objects.smarter_admin_user_profile  # type: ignore[union-attr]
            )

            combined_chatbots = user_chatbots | admin_chatbots | smarter_chatbots
            return combined_chatbots

        logger.debug(
            "%s.get_cached_chatbots_for_user_profile() - Getting chatbots for user_profile_id %s",
            logger_prefix,
            user_profile_id,
        )

        chatbot_helpers = []
        user_profile = UserProfile.objects.get(id=user_profile_id)
        admin_user = get_cached_admin_user_for_account(account=user_profile.account)
        if not admin_user:
            raise ValueError(f"No admin user found for account {user_profile.account}")
        admin_user_profile = get_cached_user_profile(user=admin_user)

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
                request=None,  # type: ignore[assignment]
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
