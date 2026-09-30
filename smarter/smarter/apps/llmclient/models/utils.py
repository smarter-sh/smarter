"""Utility functions for the LLMClient app, including caching and validation helpers."""

from typing import Optional

from django.http import HttpRequest

from smarter.common.helpers.console_helpers import (
    formatted_text,
)
from smarter.common.utils import smarter_build_absolute_uri
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

from .llmclient import LLMClient
from .llmclient_helper import LLMClientHelper

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


def get_cached_llmclient_by_request(request: HttpRequest) -> Optional[LLMClient]:
    """
    Returns the llmclient from the cache if it exists, otherwise.

    it queries the database with assistance from LLMClientHelper
    and caches the result.

    .. code-block:: python

        llmclient = get_cached_llmclient_by_request(request)
        print(llmclient.url)

    param request: The Django HttpRequest object containing the URL and user context.
    type request: django.http.HttpRequest
    returns: The LLMClient instance associated with the request URL, or None if not found.
    rtype: Optional[LLMClient]
    """

    # pylint: disable=W0613
    @cache_results()
    def get_llmclient_by_url(url: str, class_name: str) -> Optional[LLMClient]:
        """
        We use the request URL as the cache key to avoid redundant.

        parsing and database queries for repeated requests.
        """
        llmclient_helper = LLMClientHelper(request)
        if llmclient_helper:
            logger.debug(
                "%s.get_cached_llmclient_by_request() resolved and cached llmclient '%s' for url: %s",
                formatted_text(__name__),
                llmclient_helper.llmclient,
                url,
            )
        return llmclient_helper.llmclient

    if not request:
        return None
    url = smarter_build_absolute_uri(request)
    return get_llmclient_by_url(url=url, class_name=LLMClient.__name__)


__all__ = [
    "get_cached_llmclient_by_request",
]
