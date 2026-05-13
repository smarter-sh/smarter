"""
Utility functions for the ChatBot app, including caching and validation helpers.
"""

from typing import Optional

from django.http import HttpRequest

from smarter.common.helpers.console_helpers import (
    formatted_text,
)
from smarter.common.utils import smarter_build_absolute_uri
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

from .chatbot import ChatBot
from .chatbot_helper import ChatBotHelper

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CHATBOT_LOGGING])


def get_cached_chatbot_by_request(request: HttpRequest) -> Optional[ChatBot]:
    """
    Returns the chatbot from the cache if it exists, otherwise
    it queries the database with assistance from ChatBotHelper
    and caches the result.

    .. code-block:: python

        chatbot = get_cached_chatbot_by_request(request)
        print(chatbot.url)

    param request: The Django HttpRequest object containing the URL and user context.
    type request: django.http.HttpRequest
    returns: The ChatBot instance associated with the request URL, or None if not found.
    rtype: Optional[ChatBot]
    """

    # pylint: disable=W0613
    @cache_results()
    def get_chatbot_by_url(url: str, class_name: str) -> Optional[ChatBot]:
        """
        We use the request URL as the cache key to avoid redundant
        parsing and database queries for repeated requests.
        """
        chatbot_helper = ChatBotHelper(request)
        if chatbot_helper:
            logger.debug(
                "%s.get_cached_chatbot_by_request() resolved and cached chatbot '%s' for url: %s",
                formatted_text(__name__),
                chatbot_helper.chatbot,
                url,
            )
        return chatbot_helper.chatbot

    if not request:
        return None
    url = smarter_build_absolute_uri(request)
    return get_chatbot_by_url(url=url, class_name=ChatBot.__name__)


__all__ = [
    "get_cached_chatbot_by_request",
]
