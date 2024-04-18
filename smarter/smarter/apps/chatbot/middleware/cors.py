"""
This module contains the middleware for handling CORS headers for the application.
It adds chatbot urls to the CORS_ALLOWED_ORIGINS list at run-time.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Pattern, Sequence
from urllib.parse import SplitResult, urlsplit

from corsheaders.conf import conf
from corsheaders.middleware import CorsMiddleware as DjangoCorsMiddleware
from django.http import HttpRequest

from smarter.apps.chatbot.models import ChatBotApiUrlHelper


logger = logging.getLogger(__name__)


class CorsMiddleware(DjangoCorsMiddleware):
    """CORSMiddleware is used to handle CORS headers for the application."""

    @lru_cache(maxsize=10)
    def CORS_ALLOWED_ORIGINS(self, url: SplitResult = None) -> list[str] | tuple[str]:
        """
        Returns the list of allowed origins for the application. If the request
        is from a chatbot, the chatbot url is added to the list.
        """
        if url is None:
            return conf.CORS_ALLOWED_ORIGINS
        chatbot_url = ChatBotApiUrlHelper(url=url.geturl())
        if chatbot_url.chatbot:
            logger.info("Adding chatbot url to CORS_ALLOWED_ORIGINS: %s", chatbot_url.url)
            return conf.CORS_ALLOWED_ORIGINS + [chatbot_url.url]
        return conf.CORS_ALLOWED_ORIGINS

    @property
    def CORS_ALLOWED_ORIGIN_REGEXES(self) -> Sequence[str | Pattern[str]]:
        # FIX NOTE: ADD CHATBOT URL
        return conf.CORS_ALLOWED_ORIGIN_REGEXES

    @property
    def CORS_URLS_REGEX(self) -> str | Pattern[str]:
        # FIX NOTE: ADD CHATBOT URL
        return conf.CORS_URLS_REGEX

    def origin_found_in_white_lists(self, origin: str, url: SplitResult) -> bool:
        return (
            (origin == "null" and origin in self.CORS_ALLOWED_ORIGINS(url=url))
            or self._url_in_whitelist(url)
            or self.regex_domain_match(origin)
        )

    def regex_domain_match(self, origin: str) -> bool:
        return any(re.match(domain_pattern, origin) for domain_pattern in self.CORS_ALLOWED_ORIGIN_REGEXES)

    def is_enabled(self, request: HttpRequest) -> bool:
        return bool(re.match(self.CORS_URLS_REGEX, request.path_info)) or self.check_signal(request)

    def _url_in_whitelist(self, url: SplitResult) -> bool:
        origins = [urlsplit(o) for o in self.CORS_ALLOWED_ORIGINS(url=url)]
        return any(origin.scheme == url.scheme and origin.netloc == url.netloc for origin in origins)
