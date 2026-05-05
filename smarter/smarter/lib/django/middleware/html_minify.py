# pylint: disable=W0613
"""Middleware to minify HTML"""

import inspect
import logging

from asgiref.sync import markcoroutinefunction
from bs4 import BeautifulSoup, Comment
from django.http import FileResponse
from django.utils.deprecation import MiddlewareMixin

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING) or waffle.switch_is_active(
        SmarterWaffleSwitches.MIDDLEWARE_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
logger.debug("Loading %s", formatted_text(__name__ + ".HTMLMinifyMiddleware"))


class HTMLMinifyMiddleware(MiddlewareMixin):
    """
    Middleware to minify HTML using BeautifulSoup. It removes comments and
    unnecessary whitespace from the HTML content of the response.
    It skips minification for certain paths and content types to avoid
    issues with non-HTML responses.
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        self.is_async = inspect.iscoroutinefunction(get_response)
        if self.is_async:
            markcoroutinefunction(self)

    def _should_skip(self, request, response) -> bool:
        """Return True if minification should be skipped for this request/response."""
        if isinstance(response, FileResponse):
            return True
        if not hasattr(response, "content") or not response.content:
            return True
        if hasattr(request, "path"):
            path = str(request.path)
            if path in ["/robots.txt", "/favicon.ico", "/sitemap.xml"]:
                return True
            if path.startswith("/static/") or path.startswith("/media/"):
                return True
            if path.startswith("/api/"):
                return True
            if path.endswith(".xml") or path.endswith(".rss") or path.endswith(".feed"):
                return True
        return False

    def _minify(self, response):
        """Apply BeautifulSoup minification to the response in-place and return it."""
        content = response.content
        if "text/html" not in response["Content-Type"]:
            return response
        try:
            content_str = (
                content.lstrip().decode("utf-8", errors="replace") if isinstance(content, bytes) else content.lstrip()
            )
            if (
                content_str.startswith("<?xml")
                or content_str.startswith("<rss")
                or content_str.startswith("<feed")
                or content_str.startswith("<sitemap")
            ):
                return response
            soup = BeautifulSoup(content, "lxml")
            for comment in soup.findAll(text=lambda text: isinstance(text, Comment)):  # type: ignore
                comment.extract()
            soup_string = soup.prettify(formatter="minimal")
            response.content = soup_string.encode("utf-8") if isinstance(soup_string, str) else soup_string
            response["Content-Length"] = str(len(response.content))
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("Error minifying HTML: %s", e)
        return response

    def process_response(self, request, response):
        if self._should_skip(request, response):
            return response
        return self._minify(response)

    async def async_process_response(self, request, response):
        if self._should_skip(request, response):
            return response
        return self._minify(response)
