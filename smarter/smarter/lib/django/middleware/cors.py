"""
This module contains the middleware for handling CORS headers for the application.
It adds chatbot urls to the CORS_ALLOWED_ORIGINS list at run-time.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable
from typing import Pattern, Sequence
from urllib.parse import SplitResult, urlparse, urlsplit

import waffle
from corsheaders.conf import conf
from corsheaders.middleware import CorsMiddleware as DjangoCorsMiddleware
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest
from django.http.response import HttpResponseBase

from smarter.apps.chatbot.models import ChatBot, get_cached_chatbot_by_request
from smarter.common.classes import SmarterHelperMixin
from smarter.common.const import SmarterWaffleSwitches


logger = logging.getLogger(__name__)

if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
    logger.info("Loading smarter.lib.django.middleware.cors.CorsMiddleware")


class CorsMiddleware(DjangoCorsMiddleware, SmarterHelperMixin):
    """CORSMiddleware is used to handle CORS headers for the application."""

    _url: SplitResult = None
    _chatbot: ChatBot = None
    request: WSGIRequest = None

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:
        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
            url = request.build_absolute_uri()
            logger.info("%s.__call__() - url=%s", self.formatted_class_name, url)
        self._url = None
        self._chatbot = None
        self.request = request
        return super().__call__(request)  # Ensure the response is returned

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
        if url_string in conf.CORS_ALLOWED_ORIGINS:
            if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
                logger.info("%s url: %s is an allowed origin", self.formatted_class_name, url.geturl())
            return None

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
            logger.info("%s instantiating ChatBotHelper() for url: %s", self.formatted_class_name, url.geturl())
        self._chatbot = get_cached_chatbot_by_request(request=self.request)

        # If the chatbot is found, update the chatbot url
        # which ensures that we'll only be working with the
        # base url for the chatbot and that the protocol
        # will remain consistent.
        if self.chatbot:
            self._url = self.chatbot.url
        else:
            self._url = url

        if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
            logger.info("%s.url() set url: %s", self.formatted_class_name, self._url.geturl() if self.url else None)

    @property
    def CORS_ALLOWED_ORIGINS(self) -> list[str] | tuple[str]:
        """
        Returns the list of allowed origins for the application. If the request
        is from a chatbot, the chatbot url is added to the list.
        """
        retval = conf.CORS_ALLOWED_ORIGINS.copy()
        if self.chatbot is not None:
            url = self.url.geturl()
            retval.append(url)
            if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
                logger.info("%s.CORS_ALLOWED_ORIGINS() added origin: %s", self.formatted_class_name, url)
        return retval

    @property
    def CORS_ALLOWED_ORIGIN_REGEXES(self) -> Sequence[str | Pattern[str]]:
        # FIX NOTE: ADD CHATBOT URL
        return conf.CORS_ALLOWED_ORIGIN_REGEXES

    def origin_found_in_white_lists(self, origin: str, url: SplitResult) -> bool:
        self.url = url
        if self.chatbot is not None:
            if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
                logger.info("%s.origin_found_in_white_lists() returning True: %s", self.formatted_class_name, url)
            return True
        return (
            (origin == "null" and origin in self.CORS_ALLOWED_ORIGINS)
            or self._url_in_whitelist(url)
            or self.regex_domain_match(origin)
        )

    def regex_domain_match(self, origin: str) -> bool:
        if self.chatbot is not None:
            if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
                logger.info("%s.regex_domain_match() returning True: %s", self.formatted_class_name, url)
            return True
        return any(re.match(domain_pattern, origin) for domain_pattern in self.CORS_ALLOWED_ORIGIN_REGEXES)

    def _url_in_whitelist(self, url: SplitResult) -> bool:
        self.url = url
        if self.chatbot is not None:
            if waffle.switch_is_active(SmarterWaffleSwitches.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING):
                logger.info("%s._url_in_whitelist() returning True: %s", self.formatted_class_name, url)
            return True
        origins = [urlsplit(o) for o in self.CORS_ALLOWED_ORIGINS]
        return any(origin.scheme == url.scheme and origin.netloc == url.netloc for origin in origins)
