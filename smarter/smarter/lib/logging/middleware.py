"""
smarter.lib.logging.middleware
==============================

Middleware for Per-Request Logging Context
------------------------------------------

This module provides Django middleware that injects a per-request logging context into Python's
``contextvars`` system. This enables:

- **Request-scoped logging correlation**: Each HTTP request receives a unique logging context, allowing logs to be traced per request.
- **Async-safe logging context propagation**: Works seamlessly with both synchronous and asynchronous Django views, ensuring context is preserved across async boundaries.
- **Real-time log filtering**: Supports real-time log filtering in the Smarter Terminal Emulator for improved debugging and monitoring.
- **User-scoped or anonymous request tracing**: Authenticated users are identified in logs by their model and username; anonymous users receive a UUID-based identifier.

Features
--------

- Integrates with Django's middleware stack.
- Uses context variables for safe, per-request logging context.
- Supports both sync and async Django request handling.
- Controlled by a Waffle switch (``SmarterWaffleSwitches.ENABLE_MIDDLEWARE_REQUEST_LOG_CONTEXT``).

Usage
-----

Add ``SmarterRequestLogContextMiddleware`` to your Django ``MIDDLEWARE`` settings to enable per-request logging context. Ensure the required Waffle switch is configured to activate the middleware.

.. code-block:: python

    MIDDLEWARE = [
        # ...
        'smarter.lib.logging.middleware.SmarterRequestLogContextMiddleware',
        # ...
    ]

Dependencies
------------

- Django
- asgiref
- smarter.common.helpers.logger_helpers
- smarter.common.mixins
- smarter.lib.logging.redis_log_handler
- smarter.lib.django.waffle

"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextvars import Token
from typing import cast

from django.http import HttpRequest, HttpResponseBase

from smarter.common.helpers.logger_helpers import formatted_text
from smarter.common.mixins import SmarterMiddlewareMixin
from smarter.common.mixins.helper_mixin import SmarterHelperMixin
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .redis_log_handler import (
    get_user_context,
    job_id_factory,
    user_id_context,
)

# logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MIDDLEWARE_LOGGING])
logger = logging.getSmarterLogger(__name__)

if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_REQUEST_LOG_CONTEXT):
    logger.debug(
        "%s is %s",
        formatted_text(__name__ + ".SmarterRequestLogContextMiddleware"),
        SmarterHelperMixin().formatted_state_ready,
    )
else:
    logger.debug(
        "%s is %s. Enable with Django waffle in the admin console.",
        formatted_text(__name__ + ".SmarterRequestLogContextMiddleware"),
        SmarterHelperMixin().formatted_state_not_ready,
    )


class SmarterRequestLogContextMiddleware(SmarterMiddlewareMixin):
    """
    Middleware that injects request identity into logging contextvars.

    Authenticated users receive:
        "<ModelClass>.<username>"

    Anonymous users receive:
        UUID-based request identifiers.
    """

    sync_capable = True
    async_capable = True

    def __call__(self, request: HttpRequest) -> Awaitable[HttpResponseBase] | HttpResponseBase:

        if self.async_mode:
            return self.__acall__(request)

        if self.deserves_amnesty(request.path):
            return self.get_response(request)

        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_REQUEST_LOG_CONTEXT):
            return self.get_response(request)

        context = self.get_sync_context(request)
        logger.debug("%s called. Setting context=%s", self.formatted_class_name, context)
        token = self.set_logging_context(context)
        # purge_log_context(context)

        try:
            return self.get_response(request)
        finally:
            self.reset_logging_context(token)
            logger.debug("%s reset logging context=%s", self.formatted_class_name, context)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:

        async_get_response = cast(Callable[[HttpRequest], Awaitable[HttpResponseBase]], self.get_response)

        if not await waffle.async_switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_REQUEST_LOG_CONTEXT):
            return await async_get_response(request)

        context = await self.get_async_context(request)

        logger.debug("%s setting async logging context=%s", self.formatted_class_name, context)
        token = self.set_logging_context(context)

        try:
            return await async_get_response(request)
        finally:
            self.reset_logging_context(token)
            logger.debug("%s reset async logging context=%s", self.formatted_class_name, context)

    @property
    def formatted_class_name(self) -> str:
        return formatted_text(f"{__name__}.{self.__class__.__name__}[{id(self)}]")

    @staticmethod
    def set_logging_context(context: str) -> Token:
        """
        Set request-scoped logging context.
        """

        return user_id_context.set(context)

    @staticmethod
    def reset_logging_context(token: Token) -> None:
        """
        Restore previous logging context.
        """

        user_id_context.reset(token)

    def get_sync_context(self, request: HttpRequest) -> str:
        """
        Resolve logging context for sync requests.
        """

        user = getattr(request, "user", None)

        if self.is_authenticated(user):
            return get_user_context(user)

        return job_id_factory()

    async def get_async_context(self, request: HttpRequest) -> str:
        """
        Resolve logging context for async requests.
        """

        auser = getattr(request, "auser", None)

        if auser is None:
            return job_id_factory()

        user = await auser()

        if self.is_authenticated(user):
            return get_user_context(user)

        return job_id_factory()

    @staticmethod
    def is_authenticated(user) -> bool:
        """
        Safely determine whether a user is authenticated.
        """

        return bool(user is not None and getattr(user, "is_authenticated", False))
