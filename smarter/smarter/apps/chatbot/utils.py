from functools import lru_cache
from logging import getLogger

from smarter.apps.account.models import Account
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import ChatBot


logger = getLogger(__name__)

LRU_CACHE_MAX_SIZE = 128


@cache_results()
def get_cached_chatbot(chatbot_name: str = None, chatbot_account: Account = None, chatbot_id: int = None) -> ChatBot:
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
            logger.info("_in_memory_chatbot_by_id() retrieving and caching chatbot %s", chatbot)
        return chatbot

    # pylint: disable=W0613
    @lru_cache(maxsize=LRU_CACHE_MAX_SIZE)
    def _in_memory_chatbot_by_name(chatbot_name, chatbot_account_number):
        """
        In-memory cache for chatbot objects by chatbot number.
        """
        chatbot = ChatBot.objects.get(name=chatbot_name, account=chatbot_account)
        if waffle.switch_is_active(SmarterWaffleSwitches.CACHE_LOGGING):
            logger.info("_in_memory_chatbot_by_number() retrieving and caching chatbot %s", chatbot)
        return chatbot

    if chatbot_id:
        return _in_memory_chatbot_by_id(chatbot_id=chatbot_id)

    account_number = chatbot_account.chatbot_number if chatbot_account else None
    if chatbot_name and account_number:
        return _in_memory_chatbot_by_name(chatbot_name=chatbot_name, chatbot_account_number=account_number)
