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

from .llm_client import LLMClient
from .llm_client_helper import LLMClientHelper

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


def get_cached_llm_client_by_request(request: HttpRequest) -> Optional[LLMClient]:
    """
    Returns the llm_client from the cache if it exists, otherwise.

    it queries the database with assistance from LLMClientHelper
    and caches the result.

    .. code-block:: python

        llm_client = get_cached_llm_client_by_request(request)
        print(llm_client.url)

    param request: The Django HttpRequest object containing the URL and user context.
    type request: django.http.HttpRequest
    returns: The LLMClient instance associated with the request URL, or None if not found.
    rtype: Optional[LLMClient]
    """

    # pylint: disable=W0613
    @cache_results()
    def get_llm_client_by_url(url: str, class_name: str) -> Optional[LLMClient]:
        """
        We use the request URL as the cache key to avoid redundant.

        parsing and database queries for repeated requests.
        """
        llm_client_helper = LLMClientHelper(request)
        if llm_client_helper:
            logger.debug(
                "%s.get_cached_llm_client_by_request() resolved and cached llm_client '%s' for url: %s",
                formatted_text(__name__),
                llm_client_helper.llm_client,
                url,
            )
        return llm_client_helper.llm_client

    if not request:
        return None
    url = smarter_build_absolute_uri(request)
    return get_llm_client_by_url(url=url, class_name=LLMClient.__name__)


__all__ = [
    "get_cached_llm_client_by_request",
]
