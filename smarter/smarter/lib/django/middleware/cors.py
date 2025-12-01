"""
This module contains the middleware for handling CORS headers for the application.
It adds chatbot urls to the CORS_ALLOWED_ORIGINS list at run-time.
"""

import logging
import re
from collections.abc import Awaitable
from typing import Optional, Pattern, Sequence
from urllib.parse import SplitResult, urlsplit

from corsheaders.conf import conf
from corsheaders.middleware import CorsMiddleware
from django.conf import settings
from django.http import HttpRequest
from django.http.response import HttpResponseBase

from smarter.apps.chatbot.models import ChatBot, get_cached_chatbot_by_request
from smarter.common.classes import SmarterHelperMixin
from smarter.common.conf import settings as smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import SmarterHttpResponseServerError
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.MIDDLEWARE_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

logger.info("Loading smarter.lib.django.middleware.cors.SmarterCorsMiddleware")


class SmarterCorsMiddleware(CorsMiddleware, SmarterHelperMixin):
    """SmarterCorsMiddleware is used to handle CORS headers for the application."""

    _url: Optional[SplitResult] = None
    _chatbot: Optional[ChatBot] = None
    request: Optional[HttpRequest] = None

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:

        host = request.get_host()
        if not host:
            return SmarterHttpResponseServerError(
                request=request,
                error_message="Internal error (500) - could not parse request.",
            )

        # Short-circuit for health checks
        if request.path.replace("/", "") in self.amnesty_urls:
            return super().__call__(request)

        # Short-circuit for any requests born from internal IP address hosts
        # This is unlikely, but not impossible.
        if any(host.startswith(prefix) for prefix in settings.INTERNAL_IP_PREFIXES):
            logger.info(
                "%s %s identified as an internal IP address, exiting.",
                self.formatted_class_name,
                self.smarter_build_absolute_uri(request),
            )
            return super().__call__(request)

        url = self.smarter_build_absolute_uri(request)
        logger.info("%s.__call__() - url=%s", self.formatted_class_name, url)
        self._url = None
        self._chatbot = None
        self.request = request
        return super().__call__(request)  # Ensure the response is returned

    @property
    def chatbot(self) -> Optional[ChatBot]:
        return self._chatbot

    @property
    def url(self) -> Optional[SplitResult]:
        if isinstance(self._url, SplitResult):
            return self._url

    @url.setter
    def url(self, url: Optional[SplitResult] = None):

        url_string = url.geturl() if isinstance(url, SplitResult) else None
        if url_string in conf.CORS_ALLOWED_ORIGINS:
            logger.info(
                "%s url: %s is an allowed origin",
                self.formatted_class_name,
                url.geturl() if isinstance(url, SplitResult) else "(Missing URL)",
            )
            return None

        logger.info(
            "%s instantiating ChatBotHelper() for url: %s",
            self.formatted_class_name,
            url.geturl() if isinstance(url, SplitResult) else "(Missing URL)",
        )
        if self.request is not None:
            self._chatbot = get_cached_chatbot_by_request(request=self.request)

        # If the chatbot is found, update the chatbot url
        # which ensures that we'll only be working with the
        # base url for the chatbot and that the protocol
        # will remain consistent.
        if self.chatbot:
            self._url = urlsplit(self.chatbot.url)  # type: ignore[assignment]
        else:
            self._url = url

        logger.info(
            "%s.url() set url: %s", self.formatted_class_name, self._url.geturl() if self._url else "(Missing URL)"
        )

    @property
    def CORS_ALLOWED_ORIGINS(self) -> list[str] | tuple[str]:
        """
        Returns the list of allowed origins for the application. If the request
        is from a chatbot, the chatbot url is added to the list.
        """
        retval = (
            conf.CORS_ALLOWED_ORIGINS.copy()
            if isinstance(conf.CORS_ALLOWED_ORIGINS, list)
            else list(conf.CORS_ALLOWED_ORIGINS)
        )
        if self.chatbot is not None:
            url = self.url.geturl() if isinstance(self.url, SplitResult) else None
            if url is not None and url not in retval:
                retval.append(url)
            logger.info("%s.CORS_ALLOWED_ORIGINS() added origin: %s", self.formatted_class_name, url)
        return retval

    @property
    def CORS_ALLOWED_ORIGIN_REGEXES(self) -> Sequence[str | Pattern[str]]:
        # FIX NOTE: ADD CHATBOT URL
        return conf.CORS_ALLOWED_ORIGIN_REGEXES

    def origin_found_in_white_lists(self, origin: str, url: SplitResult) -> bool:
        self.url = url
        if self.chatbot is not None:
            logger.info("%s.origin_found_in_white_lists() returning True: %s", self.formatted_class_name, url)
            return True
        return (
            (origin == "null" and origin in self.CORS_ALLOWED_ORIGINS)
            or self._url_in_whitelist(url)
            or self.regex_domain_match(origin)
        )

    def regex_domain_match(self, origin: str) -> bool:
        if self.chatbot is not None:
            logger.info("%s.regex_domain_match() returning True: %s", self.formatted_class_name, self.url)
            return True
        return any(re.match(domain_pattern, origin) for domain_pattern in self.CORS_ALLOWED_ORIGIN_REGEXES)

    def _url_in_whitelist(self, url: SplitResult) -> bool:
        self.url = url
        if self.chatbot is not None:
            logger.info("%s._url_in_whitelist() returning True: %s", self.formatted_class_name, url)
            return True
        origins = [urlsplit(o) for o in self.CORS_ALLOWED_ORIGINS]
        return any(origin.scheme == url.scheme and origin.netloc == url.netloc for origin in origins)
