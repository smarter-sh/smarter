# pylint: disable=unused-argument
"""
Middleware for safely minifying HTML responses in Django applications.

This middleware reduces HTML response size by removing HTML comments
and serializing markup using a minimal formatter while preserving
response correctness and compatibility with both sync and async
execution models.

Key Features
============

- Removes HTML comments from responses
- Skips binary, streaming, and file responses
- Preserves non-HTML content types
- Safely updates ``Content-Length`` headers
- Supports sync and async Django execution
- Fail-safe behavior on parsing errors
- Feature-flag enablement via Django Waffle

Behavior
========

For each response, the middleware:

#. Verifies middleware feature-flag enablement
#. Detects whether the response should be skipped
#. Decodes HTML content safely
#. Detects XML and feed-like responses
#. Parses HTML using BeautifulSoup
#. Removes HTML comments
#. Serializes minimized HTML
#. Updates response content and headers

If minification fails for any reason, the original response is returned
unchanged.

Supported Response Types
========================

The middleware only processes standard HTML responses.

The following response types are intentionally skipped:

- file downloads
- streaming responses
- API responses
- XML responses
- RSS and feed documents
- static/media assets
- non-HTML content types

Skip Rules
===========

Requests are skipped when:

- the response is a ``FileResponse``
- the response is streaming
- the response has no content
- the content type is not ``text/html``
- the request path matches excluded paths
- the request path matches excluded prefixes
- the request path matches excluded suffixes
- the response appears to contain XML content

Default Excluded Path Prefixes
==============================

The middleware skips paths beginning with:

- ``/static/``
- ``/media/``
- ``/api/``

Default Excluded Paths
======================

The middleware skips several well-known non-HTML endpoints:

- ``/robots.txt``
- ``/favicon.ico``
- ``/sitemap.xml``

Async Compatibility
===================

The middleware supports both synchronous and asynchronous Django
execution models.

Async response processing uses ``async_process_response()`` and delegates
CPU-bound HTML parsing through ``sync_to_async()``.

Coroutine-based request handlers are detected automatically during
middleware initialization.

HTML Processing
===============

HTML parsing and serialization are performed using BeautifulSoup with
the ``lxml`` parser backend.

Comment removal targets standard HTML comment nodes only.

Serialized output uses BeautifulSoup's ``minimal`` formatter to preserve
valid HTML structure while reducing unnecessary formatting overhead.

Content-Length Handling
=======================

After minification completes, the middleware recalculates and updates
the ``Content-Length`` response header to ensure HTTP correctness.

Logging
=======

The middleware emits structured logs for:

- middleware initialization
- successful response minification
- HTML parsing failures

Failures are logged without interrupting the request lifecycle.

Classes
=======

.. autosummary::
   :toctree: generated/

   HTMLMinifyMiddleware

Dependencies
============

- Django
- BeautifulSoup4
- lxml
- asgiref
- Django Waffle

Warnings
========

HTML minification is intentionally conservative and does not attempt
aggressive whitespace collapsing or JavaScript/CSS optimization.

Malformed HTML documents may serialize differently after parsing.

Notes
=====

This middleware inherits from
:class:`django.utils.deprecation.MiddlewareMixin`
for compatibility with Django's middleware lifecycle hooks.

The middleware is designed to be fail-safe. Any parsing or serialization
errors automatically fall back to the original unmodified response.
"""

from __future__ import annotations

from collections.abc import Awaitable

from asgiref.sync import sync_to_async
from bs4 import BeautifulSoup, Comment
from django.http import FileResponse, HttpRequest, HttpResponseBase

from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin, SmarterMiddlewareMixin
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__)
if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_HTML_MINIFY):
    logger.debug(
        "%s is %s",
        formatted_text(__name__ + ".HTMLMinifyMiddleware"),
        SmarterHelperMixin().formatted_state_ready,
    )
else:
    logger.debug(
        "%s is %s. Enable with Django waffle in the admin console.",
        formatted_text(__name__ + ".HTMLMinifyMiddleware"),
        SmarterHelperMixin().formatted_state_not_ready,
    )


class HTMLMinifyMiddleware(SmarterMiddlewareMixin):
    """
    Middleware that minifies HTML responses using BeautifulSoup.

    Notes:
    - Only processes HTML responses
    - Skips streaming/file responses
    - Fail-safe: original response is returned on parsing errors
    """

    SKIP_PATH_PREFIXES = (
        "/static/",
        "/media/",
        "/api/",
    )

    SKIP_PATHS = frozenset(
        {
            "/robots.txt",
            "/favicon.ico",
            "/sitemap.xml",
        }
    )

    SKIP_SUFFIXES = (
        ".xml",
        ".rss",
        ".feed",
    )

    XML_PREFIXES = (
        "<?xml",
        "<rss",
        "<feed",
        "<sitemap",
    )

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:

        if self.async_mode:
            return self.__acall__(request)

        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_HTML_MINIFY):
            return self.get_response(request)

        logger.debug("%s.__call__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)
        response = self.get_response(request)
        response = self.process_response(request, response)

        if response is not None:
            return response

        return self.get_response(request)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:

        if not await waffle.async_switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_HTML_MINIFY):
            return await sync_to_async(self.get_response)(request)

        logger.debug("%s.__acall__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)
        response = await sync_to_async(self.get_response)(request)
        response = await self.async_process_response(request, response)
        return response

    @property
    def formatted_class_name(self) -> str:
        return formatted_text(f"{__name__}.{self.__class__.__name__}[{id(self)}]")

    def process_response(self, request: HttpRequest, response):

        if self.should_skip(request, response):
            return response

        return self.minify_response(response)

    async def async_process_response(self, request, response):

        if self.should_skip(request, response):
            return response

        return await sync_to_async(self.minify_response)(response)

    def should_skip(self, request: HttpRequest, response) -> bool:
        """
        Determine whether minification should be skipped.
        """

        if isinstance(response, FileResponse):
            return True

        if getattr(response, "streaming", False):
            return True

        if not hasattr(response, "content"):
            return True

        if not response.content:
            return True

        content_type = response.get("Content-Type", "").lower()

        if "text/html" not in content_type:
            return True

        path = str(getattr(request, "path", "")).lower()

        if path in self.SKIP_PATHS:
            return True

        if path.endswith(self.SKIP_SUFFIXES):
            return True

        for prefix in self.SKIP_PATH_PREFIXES:
            if path.startswith(prefix):
                return True

        return False

    def minify_response(self, response):
        """
        Minify HTML response content.
        """

        try:

            html = self.decode_content(response.content)

            if self.looks_like_xml(html):
                return response

            soup = BeautifulSoup(html, "lxml")
            self.remove_comments(soup)
            minified_html = self.serialize_html(soup)
            response.content = minified_html.encode("utf-8")
            response["Content-Length"] = str(len(response.content))

            logger.debug("%s minified HTML response", self.formatted_class_name)

        except Exception as exc:  # pylint: disable=broad-except
            logging.exception("%s failed to minify HTML: %s", self.formatted_class_name, exc)

        return response

    @staticmethod
    def decode_content(content) -> str:
        """
        Decode response content safely.
        """

        if isinstance(content, bytes):
            return content.decode("utf-8", errors="replace").lstrip()

        return str(content).lstrip()

    @classmethod
    def looks_like_xml(cls, html: str) -> bool:
        """
        Detect XML/RSS/Feed responses.
        """

        html = html.lower()

        return any(html.startswith(prefix) for prefix in cls.XML_PREFIXES)

    @staticmethod
    def remove_comments(soup: BeautifulSoup) -> None:
        """
        Remove HTML comments from soup.
        """

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

    @staticmethod
    def serialize_html(soup: BeautifulSoup) -> str:
        """
        Serialize minimized HTML.
        """

        return soup.decode(formatter="minimal")
