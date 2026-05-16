"""
ASGI-safe dynamic CORS middleware for Django.

This module extends :class:`corsheaders.middleware.CorsMiddleware`
to support dynamically generated, request-scoped CORS origins while
remaining fully compatible with concurrent ASGI execution.

The middleware is specifically designed to safely support chatbot-origin
resolution without introducing cross-request state leakage or unsafe
async behavior.

Key Features
============

- Fully compatible with ASGI concurrency
- Stateless request processing
- Dynamic chatbot-specific origin allowlisting
- Local development origin support
- Compatibility with ``django-cors-headers``
- Optional feature-flag enablement via Django Waffle
- Internal network bypass support
- Regex-based origin matching

Concurrency Safety
==================

This middleware intentionally avoids several patterns that commonly
cause race conditions or request leakage under ASGI:

- No mutable request state persisted across requests
- No ``cached_property`` usage for request-specific data
- No ``functools.lru_cache`` usage on request-dependent methods
- No custom async adaptation
- No ``markcoroutinefunction`` usage
- No shared mutable global state

Request state is attached only temporarily during request processing
and is always cleaned up immediately afterward.

Behavior
========

For each request, the middleware:

#. Starts with the configured static CORS allowlist
#. Dynamically resolves chatbot-specific origins
#. Adds localhost development origins when appropriate
#. Applies regex-based origin matching
#. Defers to ``django-cors-headers`` for core CORS behavior

If the corresponding Django Waffle switch is disabled, the middleware
acts as a transparent pass-through.

Classes
=======

.. autosummary::
   :toctree: generated/

   SmarterCorsMiddleware

Dependencies
============

- ``django-cors-headers``
- Django
- Django Waffle

Environment-Specific Behavior
=============================

In local development environments, localhost origins are automatically
added for requests targeting the local API host.

Internal IP prefixes defined in application settings may bypass
middleware processing entirely.

Logging
=======

Middleware lifecycle events, dynamic origin additions, and exception
conditions are logged using the application's structured logging
framework.

Notes
=====

This middleware relies on request-scoped chatbot resolution using
:func:`smarter.apps.chatbot.models.get_cached_chatbot_by_request`.

Because ``django-cors-headers`` internally expects synchronous
middleware semantics, this implementation preserves compatibility
without introducing custom async wrappers or coroutine adaptation.
"""

from __future__ import annotations

from collections.abc import Awaitable
from inspect import isawaitable, iscoroutinefunction

from asgiref.sync import markcoroutinefunction
from corsheaders.middleware import CorsMiddleware
from django.http import HttpRequest, HttpResponseBase

from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__)


class SmarterCorsMiddleware(CorsMiddleware, SmarterHelperMixin):
    """
    Django 6 / ASGI-safe dynamic CORS middleware.

    Design rules:
    - no shared request state on self
    - no coroutine guessing in core logic
    - single execution path (sync + async unified)

    Middleware for handling Cross-Origin Resource Sharing (CORS) headers in the application.

    This middleware extends the default CORS handling to dynamically add chatbot URLs to the
    allowed origins at runtime. It ensures that requests from valid chatbot origins are permitted
    by updating the CORS allowed origins list based on the current request context.

    The middleware also provides additional logic to handle internal IP addresses, health check
    endpoints, and logging for debugging and auditing purposes.

    :cvar _url: The parsed URL (as a :class:`urllib.parse.SplitResult`) for the current request, or None.
    :vartype _url: Optional[SplitResult]
    :cvar _chatbot: The chatbot instance associated with the current request, or None.
    :vartype _chatbot: Optional[ChatBot]
    :cvar request: The current Django HTTP request object, or None.
    :vartype request: Optional[HttpRequest]

    **Key Features**

    - Dynamically adds chatbot URLs to the CORS allowed origins list.
    - Handles requests from internal IP addresses and health check endpoints.
    - Provides detailed logging for CORS-related events and decisions.
    - Integrates with Django and the `django-cors-headers` package.

    .. note::
        - The chatbot URL is only added to the allowed origins if a chatbot is associated with the request.
        - Internal requests and health checks are short-circuited for efficiency.
        - Logging is controlled via a waffle switch and the application's log level.

    **Example**

    To enable this middleware, add it to your Django project's middleware settings::

        MIDDLEWARE = [
            ...
            'smarter.lib.django.middleware.cors.SmarterCorsMiddleware',
            ...
        ]

    :param request: The incoming HTTP request object.
    :type request: django.http.HttpRequest

    :returns: The HTTP response object, potentially with CORS headers added.
    :rtype: django.http.response.HttpResponseBase or Awaitable[HttpResponseBase]
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        super().__init__(get_response)

        self.get_response = get_response
        self.async_mode = iscoroutinefunction(get_response)

        if self.async_mode:
            markcoroutinefunction(self)

    @property
    def formatted_class_name(self) -> str:
        """Return the formatted class name for logging purposes."""
        return logging.formatted_text(f"{__name__}.{SmarterCorsMiddleware.__name__}[{id(self)}]")

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:
        if self.async_mode:
            return self.__acall__(request)

        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CORS):
            return super().get_response(request)

        logger.debug("%s.__call__() called for %s", self.formatted_class_name, self.smarter_build_absolute_uri(request))

        return super().__call__(request)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:

        if not await waffle.async_switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CORS):
            result = self.get_response(request)
            if isawaitable(result):
                return await result
            return result

        logger.debug(
            "%s.__acall__() called for %s", self.formatted_class_name, self.smarter_build_absolute_uri(request)
        )

        return await super().__acall__(request)
