"""
Smarter.lib.logging.middleware
==============================

Middleware for Per-Request Logging Context
------------------------------------------

This module provides Django middleware that injects a per-request logging context into Python's
``contextvars`` system. This enables:

- **Request-scoped logging correlation**: Each HTTP request receives a unique logging context, allowing logs to be traced per request.
- **Async-safe logging context propagation**: Works seamlessly with both synchronous and asynchronous Django views, ensuring context is preserved across async boundaries.
- **Real-time log filtering**: Supports real-time log filtering in the Smarter Terminal Emulator for improved debugging and monitoring.
- **User-scoped or anonymous request tracing**: Authenticated users are identified in logs by their model and username; anonymous users receive a UUID-based identifier.
- **Request-scoped log streams**: the request id that a web console React app sends in the ``X-Smarter-RequestId`` header is attached to every log record of the request, so that the app can stream the server logs of that one request, e.g. the Server Logs tab of the Prompt Passthrough.
- **Chat-scoped log streams**: the chat session key of a request to an LLMClient's api, its ``session_key`` query parameter, is attached to every log record of the request, so that Smarter Chat's Console can stream the server logs of that one chat.

Features
--------

- Integrates with Django's middleware stack.
- Uses context variables for safe, per-request logging context.
- Supports both sync and async Django request handling.
- Controlled by a Waffle switch (``SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_SERVER_LOGS``).

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
    request_id_context,
    session_key_context,
    user_id_context,
    valid_request_id,
    valid_session_key,
)

REQUEST_ID_HEADER = "X-Smarter-RequestId"

logger = logging.getSmarterLogger(__name__)

if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_SERVER_LOGS):
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

    The request's ``X-Smarter-RequestId`` header, when it is a valid request id, is set in
    :obj:`smarter.lib.logging.redis_log_handler.request_id_context`, so that each log record of
    the request carries it. Likewise, the request's ``session_key`` query parameter, when it is a
    valid chat session key, is set in
    :obj:`smarter.lib.logging.redis_log_handler.session_key_context`.
    """

    sync_capable = True
    async_capable = True

    def __call__(self, request: HttpRequest) -> Awaitable[HttpResponseBase] | HttpResponseBase:

        if self.async_mode:
            return self.__acall__(request)

        if self.deserves_amnesty(request.path):
            return super().__call__(request)

        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_SERVER_LOGS):
            return super().__call__(request)

        context = self.get_sync_context(request)
        logger.debug("%s called. Setting context=%s", self.formatted_class_name, context)
        token = self.set_logging_context(context)
        request_token = request_id_context.set(self.get_request_id(request))
        session_token = session_key_context.set(self.get_session_key(request))
        # purge_log_context(context)

        try:
            return self.get_response(request)
        finally:
            session_key_context.reset(session_token)
            request_id_context.reset(request_token)
            self.reset_logging_context(token)
            logger.debug("%s reset logging context=%s", self.formatted_class_name, context)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:

        async_get_response = cast(Callable[[HttpRequest], Awaitable[HttpResponseBase]], super().__acall__)

        if not await waffle.async_switch_is_active(SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_SERVER_LOGS):
            return await async_get_response(request)

        context = await self.get_async_context(request)

        logger.debug("%s setting async logging context=%s", self.formatted_class_name, context)
        token = self.set_logging_context(context)
        request_token = request_id_context.set(self.get_request_id(request))
        session_token = session_key_context.set(self.get_session_key(request))

        try:
            return await async_get_response(request)
        finally:
            session_key_context.reset(session_token)
            request_id_context.reset(request_token)
            self.reset_logging_context(token)
            logger.debug("%s reset async logging context=%s", self.formatted_class_name, context)

    @property
    def formatted_class_name(self) -> str:
        class_name = f"{__name__}.{self.__class__.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @staticmethod
    def set_logging_context(context: str) -> Token:
        """Set request-scoped logging context."""

        return user_id_context.set(context)

    @staticmethod
    def reset_logging_context(token: Token) -> None:
        """Restore previous logging context."""

        user_id_context.reset(token)

    @staticmethod
    def get_request_id(request: HttpRequest) -> str | None:
        """
        Return the request's ``X-Smarter-RequestId`` header, if it is a valid request id.

        :param request: The request.
        :type request: django.http.HttpRequest
        :return: The request id, or None.
        :rtype: str | None
        """
        headers = getattr(request, "headers", None)
        return valid_request_id(headers.get(REQUEST_ID_HEADER) if headers is not None else None)

    @staticmethod
    def get_session_key(request: HttpRequest) -> str | None:
        """
        Return the request's ``session_key`` query parameter, if it is a valid chat session key.

        Smarter Chat sends its chat session key with each request to an LLMClient's api.

        :param request: The request.
        :type request: django.http.HttpRequest
        :return: The chat session key, or None.
        :rtype: str | None
        """
        query = getattr(request, "GET", None)
        return valid_session_key(query.get("session_key") if query is not None else None)

    def get_sync_context(self, request: HttpRequest) -> str:
        """Resolve logging context for sync requests."""

        user = getattr(request, "user", None)

        if self.is_authenticated(user):
            return get_user_context(user)

        return job_id_factory()

    async def get_async_context(self, request: HttpRequest) -> str:
        """Resolve logging context for async requests."""

        auser = getattr(request, "auser", None)

        if auser is None:
            return job_id_factory()

        user = await auser()

        if self.is_authenticated(user):
            return get_user_context(user)

        return job_id_factory()

    @staticmethod
    def is_authenticated(user) -> bool:
        """Safely determine whether a user is authenticated."""

        return bool(user is not None and getattr(user, "is_authenticated", False))
