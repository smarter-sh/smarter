"""
Django middleware that injects a per-request identity token into the logging context.

This middleware solves a fundamental problem in concurrent Django applications:
log records emitted from different simultaneous requests are interleaved in the
log stream with no way to correlate them back to a single request. By injecting
a unique context value into Python's :mod:`contextvars` at the start of each
request and resetting it when the request completes, every log record emitted
during that request's lifetime automatically carries that identifier — enabling
per-request log filtering and real-time streaming in the Smarter Terminal Emulator.

**Why this is necessary**

Django can serve requests concurrently (ASGI) or in parallel (WSGI workers).
Standard Python ``logging`` has no concept of a "current request," so a naive
``extra={"job_id": ...}`` approach requires every call-site to pass the context
explicitly. :class:`contextvars.ContextVar` solves this at the framework level:
each asyncio Task or OS thread gets its own copy of the variable, so the value
set here is visible to all logging calls on that execution path without any
additional plumbing.

**Context value selection**

- Authenticated users → ``"<ModelClass>.<username>"`` (via
    :func:`~smarter.lib.logging.redis_log_handler.get_user_context`), making logs
    searchable by username in the real-time console.
- Anonymous / unauthenticated requests → a random UUID-based job ID generated
    by :func:`~smarter.lib.logging.redis_log_handler.job_id_factory`, ensuring
    every request still gets a stable, unique identifier.

**Sync / async dual support**

Django's middleware contract requires a middleware to be callable with either a
sync or async ``get_response`` callable.  This class detects which variant was
injected at construction time and marks itself as a coroutine function via
:func:`asgiref.sync.markcoroutinefunction` when needed, so ASGI servers can
``await`` it correctly.  The two code paths are:

- **Sync** — :meth:`__call__` → :meth:`_get_sync_context` (accesses
    ``request.user`` directly, which is always populated by the time middleware
    runs under WSGI).
- **Async** — :meth:`__acall__` → :meth:`_get_async_context` (awaits
    ``request.auser()`` because the ORM call that resolves the session-backed
    user must not block the event loop).

In both paths a :class:`contextvars.Token` is captured so that the context
variable can be **reset** (not merely cleared) in the ``finally`` block,
correctly restoring whatever value the outer scope had — important for test
harnesses and middleware stacks that reuse the same thread.

:param get_response: The next callable in the Django middleware chain, provided
    by the framework.  May be a regular callable or a coroutine function.
:type get_response: Callable

.. seealso::

    :class:`~smarter.lib.logging.redis_log_handler.RedisLogHandler`
        The log handler that reads ``user_id_context`` and publishes records to
        the appropriate Redis channel.

    :func:`~smarter.lib.logging.redis_log_handler.job_id_factory`
        Generates the unique job ID used for anonymous requests.

    :data:`~smarter.lib.logging.redis_log_handler.user_id_context`
        The :class:`contextvars.ContextVar` that carries the identity token.

Example Django ``MIDDLEWARE`` setting (order matters — place early so all
downstream middleware and views inherit the context)::

    MIDDLEWARE = [
        ...
        "smarter.lib.logging.middleware.SmarterRequestLogContextMiddleware",
        ...
    ]
"""

import inspect
from contextvars import Token
from typing import Awaitable

from asgiref.sync import markcoroutinefunction
from django.http import HttpRequest, HttpResponseBase

from smarter.common.mixins import SmarterMiddlewareMixin
from smarter.lib import logging

from .redis_log_handler import get_user_context, job_id_factory, user_id_context

logger = logging.getLogger(__name__)


class SmarterRequestLogContextMiddleware(SmarterMiddlewareMixin):
    """
    Injects a per-request identity token into the logging :mod:`contextvars` context.

    Each incoming HTTP request is assigned either an authenticated-user identifier
    (``"<ModelClass>.<username>"``) or a random UUID-based job ID.  That string is
    stored in :data:`~smarter.lib.logging.redis_log_handler.user_id_context` for the
    duration of the request and is read by
    :class:`~smarter.lib.logging.redis_log_handler.RedisLogHandler` when publishing
    log records to Redis, enabling per-request log filtering in the Smarter Terminal
    Emulator real-time console.

    The class supports both WSGI (synchronous) and ASGI (asynchronous) deployments.
    The correct code path is selected once at construction time, avoiding per-request
    ``isinstance`` overhead.

    :cvar sync_capable: Declares WSGI compatibility to Django's middleware loader.
    :cvar async_capable: Declares ASGI compatibility to Django's middleware loader.
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        """
        Initialise the middleware and detect the execution model.

        Calls the parent :class:`~smarter.common.mixins.SmarterMiddlewareMixin`
        initialiser, then inspects ``get_response`` to determine whether the server
        is running in async mode.  When async mode is detected the instance is marked
        as a coroutine function via :func:`asgiref.sync.markcoroutinefunction` so that
        Django's ASGI handler can ``await`` it correctly.

        :param get_response: The next callable in the Django middleware chain.
            Supplied by the framework; never call directly.
        :type get_response: Callable or Coroutine
        """

        super().__init__(get_response)
        self.get_response = get_response
        self.is_async = inspect.iscoroutinefunction(get_response)
        if self.is_async:
            markcoroutinefunction(self)
        self.logger_prefix = logging.formatted_text(f"{__name__}.{self.__class__.__name__}")

    def __call__(self, request: HttpRequest) -> Awaitable[HttpResponseBase] | HttpResponseBase:
        """
        Dispatch the request through the appropriate sync or async path.

        When the server is running under ASGI, delegates immediately to
        :meth:`__acall__` and returns the resulting coroutine so the event loop can
        await it.  Under WSGI the sync path runs inline:

        1. Resolve the context string via :meth:`_get_sync_context`.
        2. Set :data:`~smarter.lib.logging.redis_log_handler.user_id_context` and
           capture the returned :class:`~contextvars.Token`.
        3. Invoke ``get_response(request)`` inside a ``try/finally`` block.
        4. Reset the context variable in ``finally`` so the token is unconditionally
           restored — even if ``get_response`` raises.

        :param request: The incoming HTTP request.
        :type request: django.http.HttpRequest
        :returns: The HTTP response, or an awaitable that resolves to one.
        :rtype: django.http.HttpResponseBase or Awaitable[django.http.HttpResponseBase]
        """

        if self.is_async:
            return self.__acall__(request)

        context = self._get_sync_context(request)
        logger.debug("%s.__call__() setting logging context for request: %s", self.logger_prefix, context)
        token: Token = user_id_context.set(context)
        try:
            return self.get_response(request)
        finally:
            user_id_context.reset(token)
            logger.debug("%s.__call__() reset logging context for request: %s", self.logger_prefix, context)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        """
        Async entry point for ASGI deployments.

        Mirrors :meth:`__call__` but awaits both context resolution and
        ``get_response`` so the event loop is never blocked:

        1. Await :meth:`_get_async_context` to resolve the user without a
           synchronous ORM hit.
        2. Set :data:`~smarter.lib.logging.redis_log_handler.user_id_context` and
           capture the :class:`~contextvars.Token`.
        3. Await ``get_response(request)`` inside ``try/finally``.
        4. Reset the context variable unconditionally in ``finally``.

        :param request: The incoming HTTP request.
        :type request: django.http.HttpRequest
        :returns: The HTTP response.
        :rtype: django.http.HttpResponseBase
        """

        context = await self._get_async_context(request)
        logger.debug("%s.__acall__() setting logging context for request: %s", self.logger_prefix, context)
        token: Token = user_id_context.set(context)
        try:
            return await self.get_response(request)  # type: ignore[return-value]
        finally:
            user_id_context.reset(token)
            logger.debug("%s.__acall__() reset logging context for request: %s", self.logger_prefix, context)

    def _get_sync_context(self, request: HttpRequest) -> str:
        """
        Return the logging context string for a synchronous request.

        Reads ``request.user`` directly — safe under WSGI because authentication
        middleware has already populated it by this point in the stack.

        :param request: The incoming HTTP request.
        :type request: django.http.HttpRequest
        :returns: ``"<ModelClass>.<username>"`` for authenticated users, otherwise
            a fresh UUID-based job ID from
            :func:`~smarter.lib.logging.redis_log_handler.job_id_factory`.
        :rtype: str
        """

        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            return get_user_context(user)
        return job_id_factory()

    async def _get_async_context(self, request: HttpRequest) -> str:
        """
        Return the logging context string for an asynchronous request.

        Awaits ``request.auser()`` instead of reading ``request.user`` directly.
        This is required under ASGI because resolving the session-backed user
        involves a database lookup that must not block the event loop.

        Falls back to :func:`~smarter.lib.logging.redis_log_handler.job_id_factory`
        in two cases: ``request.auser`` is absent (e.g. in unit-test request
        factories that do not attach the async user resolver), or the resolved user
        is not authenticated.

        :param request: The incoming HTTP request.
        :type request: django.http.HttpRequest
        :returns: ``"<ModelClass>.<username>"`` for authenticated users, otherwise
            a fresh UUID-based job ID.
        :rtype: str
        """
        auser = getattr(request, "auser", None)
        if auser is None:
            return job_id_factory()

        user = await auser()
        if user is not None and getattr(user, "is_authenticated", False):
            return f"{user.__class__.__name__}.{user.username}"
        return job_id_factory()
