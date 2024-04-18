"""
This module contains the middleware for handling CORS headers for the application.
It adds chatbot urls to the CORS_ALLOWED_ORIGINS list at run-time.
"""

from __future__ import annotations

import logging
import re
from typing import Pattern, Sequence
from urllib.parse import SplitResult, urlparse, urlsplit, urlunparse

from corsheaders.conf import conf
from corsheaders.middleware import CorsMiddleware as DjangoCorsMiddleware
from django.http import HttpRequest

from smarter.apps.chatbot.models import ChatBot, ChatBotApiUrlHelper


logger = logging.getLogger(__name__)


class CorsMiddleware(DjangoCorsMiddleware):
    """CORSMiddleware is used to handle CORS headers for the application."""

    _url: SplitResult = None
    _chatbot: ChatBot = None
    _helper: ChatBotApiUrlHelper = None

    @property
    def chatbot(self) -> ChatBot:
        return self._chatbot

    @property
    def helper(self) -> ChatBotApiUrlHelper:
        return self._helper

    @property
    def url(self) -> SplitResult:
        return self._url

    @url.setter
    def url(self, url: SplitResult = None):
        if url == self._url:
            return
        self._url = url
        parsed_url = urlparse(url.geturl())
        url_without_path = urlunparse((parsed_url.scheme, parsed_url.netloc, "", "", "", ""))
        self._helper = ChatBotApiUrlHelper(url=url_without_path)
        self._chatbot = self._helper.chatbot if self._helper.chatbot else None

    @property
    def CORS_ALLOWED_ORIGINS(self) -> list[str] | tuple[str]:
        """
        Returns the list of allowed origins for the application. If the request
        is from a chatbot, the chatbot url is added to the list.
        """
        if self.chatbot is None:
            return conf.CORS_ALLOWED_ORIGINS
        logger.info("Adding chatbot url to CORS_ALLOWED_ORIGINS: %s", self.chatbot.url)
        return conf.CORS_ALLOWED_ORIGINS + [self.chatbot.url]

    @property
    def CORS_ALLOWED_ORIGIN_REGEXES(self) -> Sequence[str | Pattern[str]]:
        # FIX NOTE: ADD CHATBOT URL
        return conf.CORS_ALLOWED_ORIGIN_REGEXES

    @property
    def CORS_URLS_REGEX(self) -> str | Pattern[str]:
        # FIX NOTE: ADD CHATBOT URL
        return conf.CORS_URLS_REGEX

    def origin_found_in_white_lists(self, origin: str, url: SplitResult) -> bool:
        self.url = url
        return (
            (origin == "null" and origin in self.CORS_ALLOWED_ORIGINS)
            or self._url_in_whitelist(url)
            or self.regex_domain_match(origin)
        )

    def regex_domain_match(self, origin: str) -> bool:
        return any(re.match(domain_pattern, origin) for domain_pattern in self.CORS_ALLOWED_ORIGIN_REGEXES)

    def is_enabled(self, request: HttpRequest) -> bool:
        return bool(re.match(self.CORS_URLS_REGEX, request.path_info)) or self.check_signal(request)

    def _url_in_whitelist(self, url: SplitResult) -> bool:
        self.url = url
        origins = [urlsplit(o) for o in self.CORS_ALLOWED_ORIGINS]
        return any(origin.scheme == url.scheme and origin.netloc == url.netloc for origin in origins)
