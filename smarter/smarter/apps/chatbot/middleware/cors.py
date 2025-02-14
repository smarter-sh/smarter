"""
This module contains the middleware for handling CORS headers for the application.
It adds chatbot urls to the CORS_ALLOWED_ORIGINS list at run-time.
"""

from __future__ import annotations

import logging
import re
from typing import Pattern, Sequence
from urllib.parse import SplitResult, urlparse, urlsplit

import waffle
from corsheaders.conf import conf
from corsheaders.middleware import CorsMiddleware as DjangoCorsMiddleware
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest

from smarter.apps.chatbot.models import ChatBot, ChatBotHelper
from smarter.common.classes import SmarterHelperMixin
from smarter.common.const import SmarterWaffleSwitches


logger = logging.getLogger(__name__)

if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
    logger.info("Loading smarter.apps.chatbot.middleware.cors.CorsMiddleware")


class CorsMiddleware(DjangoCorsMiddleware, SmarterHelperMixin):
    """CORSMiddleware is used to handle CORS headers for the application."""

    _url: SplitResult = None
    _chatbot: ChatBot = None
    helper: ChatBotHelper = None
    request: WSGIRequest = None

    def __call__(self, request: HttpRequest):
        # You can now access the request object here
        self.request = request
        response = self.get_response(request)
        return response

    @property
    def chatbot(self) -> ChatBot:
        return self._chatbot

    @property
    def url(self) -> SplitResult:
        if self._url is None:
            return None
        return urlparse(self._url.geturl())

    @url.setter
    def url(self, url: SplitResult = None):

        url_string = url.geturl()
        if url_string in settings.CORS_ALLOWED_ORIGINS:
            if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
                logger.info("%s url: %s is an allowed origin", self.formatted_class_name, url.geturl())
            return None

        # get the chatbot helper for the url and try to find the chatbot
        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
            logger.info("%s instantiating ChatBotHelper() for url: %s", self.formatted_class_name, url.geturl())
        self.helper = ChatBotHelper(self.request)
        self._chatbot = self.helper.chatbot if self.helper.chatbot else None

        # If the chatbot is found, update the chatbot url
        # which ensures that we'll only be working with the
        # base url for the chatbot and that the protocol
        # will remain consistent.
        if self.helper and self.helper.chatbot:
            self._url = self.helper.chatbot.url
            return None

        self._url = url

    @property
    def CORS_ALLOWED_ORIGINS(self) -> list[str] | tuple[str]:
        """
        Returns the list of allowed origins for the application. If the request
        is from a chatbot, the chatbot url is added to the list.
        """
        retval = conf.CORS_ALLOWED_ORIGINS
        if self.chatbot is not None:
            retval += [self.chatbot.url]
        return retval

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
