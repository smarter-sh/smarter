"""
Middleware for throttling unauthenticated clients generating excessive
HTTP 404 responses.

This middleware detects repeated invalid URL requests from unauthenticated
clients and temporarily blocks abusive request patterns commonly associated
with automated scanners, vulnerability probes, and broken crawlers.

Key Features
============

- ASGI and WSGI compatible
- Supports sync and async middleware execution
- Per-IP throttling of repeated 404 responses
- Temporary automatic client blocking
- Low-noise sampled logging
- Feature-flag enablement via Django Waffle
- Exemption for authenticated users

Threat Mitigation
=================

This middleware helps mitigate several classes of abusive traffic:

- automated vulnerability scanners
- brute-force endpoint discovery
- malicious URL enumeration
- broken or misconfigured crawlers
- excessive invalid resource probing

Behavior
========

For each response, the middleware:

#. Detects HTTP 404 responses
#. Exempts authenticated users
#. Resolves the client IP address
#. Tracks repeated 404 activity in cache storage
#. Logs sampled probe activity
#. Temporarily blocks abusive clients after threshold exhaustion

When a client exceeds the configured threshold, the middleware returns
``HTTP 403 Forbidden`` responses for the duration of the throttle window.

Throttle Configuration
======================

The middleware uses the following default limits:

- ``THROTTLE_LIMIT`` = 25 requests
- ``THROTTLE_TIMEOUT`` = 600 seconds
- ``LOG_SAMPLE_RATE`` = every 10th event

These values may be overridden at the class level if needed.

Caching
=======

Throttle counters are stored using the application's configured cache
backend.

Each client is tracked independently using cache keys in the format:

.. code-block:: text

   excessive_404_throttle:<client_ip>

Authenticated Requests
======================

Authenticated requests are intentionally excluded from throttling to
avoid disrupting legitimate application usage or administrative activity.

Async Compatibility
===================

The middleware supports both synchronous and asynchronous Django
execution models.

Async deployments use ``async_process_response()``, while synchronous
deployments use ``process_response()``.

The middleware automatically detects coroutine-based request handlers
during initialization.

Feature Flags
=============

Middleware activation is controlled using Django Waffle:

- ``ENABLE_MIDDLEWARE_EXCESSIVE_404``

When disabled, the middleware becomes a transparent pass-through.

Logging
=======

The middleware emits structured logs for:

- middleware initialization
- client throttling events
- sampled 404 probe activity
- client IP resolution failures

To reduce log noise during large scanning events, 404 activity is logged
using configurable sampling intervals.

Classes
=======

.. autosummary::
   :toctree: generated/

   SmarterBlockExcessive404Middleware

Dependencies
============

- Django
- Django Waffle
- asgiref
- application cache backend

Warnings
========

This middleware uses IP-based throttling and may affect multiple users
sharing the same public IP address.

Care should be taken when deploying behind proxies or load balancers to
ensure accurate client IP extraction.

Notes
=====

The middleware depends on helper functionality provided by
:class:`smarter.common.mixins.SmarterMiddlewareMixin`.

Blocking state is temporary and automatically expires after the throttle
timeout period.
"""

from __future__ import annotations

from collections.abc import Awaitable
from http import HTTPStatus

from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponseBase, HttpResponseForbidden

from smarter.common.const import SMARTER_CUSTOMER_SUPPORT_EMAIL
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin, SmarterMiddlewareMixin
from smarter.common.utils import is_authenticated_request
from smarter.lib import logging
from smarter.lib.cache import lazy_cache as cache
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__)

if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_EXCESSIVE_404):
    logger.debug(
        "%s is %s",
        formatted_text(__name__ + ".SmarterBlockExcessive404Middleware"),
        SmarterHelperMixin().formatted_state_ready,
    )
else:
    logger.debug(
        "%s is %s. Enable with Django waffle in the admin console.",
        formatted_text(__name__ + ".SmarterBlockExcessive404Middleware"),
        SmarterHelperMixin().formatted_state_not_ready,
    )


class SmarterBlockExcessive404Middleware(SmarterMiddlewareMixin):
    """
    Middleware that throttles unauthenticated clients producing excessive 404s.

    This mitigates:
    - automated scanners
    - brute-force URL probing
    - broken crawlers
    - vulnerability enumeration attempts
    """

    THROTTLE_LIMIT = 25
    THROTTLE_TIMEOUT = 600

    LOG_SAMPLE_RATE = 10

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:

        if self.async_mode:
            return self.__acall__(request)

        logger.debug("%s.__call__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)

        response = self.get_response(request)
        self.process_response(request, response)
        return response

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:

        if not await waffle.async_switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_EXCESSIVE_404):
            return await sync_to_async(self.get_response)(request)

        logger.debug("%s.__acall__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)
        response = await self.get_response(request)
        await self.async_process_response(request, response)
        return response

    @property
    def formatted_class_name(self) -> str:
        return formatted_text(f"{__name__}.{self.__class__.__name__}[{id(self)}]")

    async def async_process_response(self, request: HttpRequest, response: HttpResponseBase) -> HttpResponseBase:
        """
        Async entry point for ASGI deployments.
        """

        return self._process_response(request, response)

    def process_response(self, request: HttpRequest, response: HttpResponseBase) -> HttpResponseBase:
        """
        Sync response middleware entry point.
        """

        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_EXCESSIVE_404):
            return response

        return self._process_response(request, response)

    def _process_response(self, request: HttpRequest, response: HttpResponseBase) -> HttpResponseBase:
        """
        Shared sync/async implementation.
        """

        if response.status_code != HTTPStatus.NOT_FOUND:
            return response

        # Authenticated users are exempt
        if is_authenticated_request(request):
            return response

        client_ip = self.get_client_ip(request)

        if not client_ip:
            logger.debug(
                "%s unable to determine client IP",
                self.formatted_class_name,
            )
            return response

        throttle_key = self.get_throttle_key(client_ip)

        blocked_count = cache.get(throttle_key, 0)

        self.log_404_event(
            request=request,
            client_ip=client_ip,
            blocked_count=blocked_count,
        )

        if blocked_count >= self.THROTTLE_LIMIT:

            logger.warning(
                "%s blocked client=%s count=%d",
                self.formatted_class_name,
                client_ip,
                blocked_count,
            )

            return HttpResponseForbidden(
                "Too many invalid requests detected from your IP address. "
                f"Contact {SMARTER_CUSTOMER_SUPPORT_EMAIL} for assistance."
            )

        self.increment_throttle(throttle_key)

        return response

    @classmethod
    def get_throttle_key(cls, client_ip: str) -> str:
        return f"excessive_404_throttle:{client_ip}"

    def increment_throttle(self, throttle_key: str) -> None:
        """
        Increment the client's 404 counter.
        """

        try:
            blocked_count = cache.incr(throttle_key)

        except ValueError:
            cache.set(
                throttle_key,
                1,
                timeout=self.THROTTLE_TIMEOUT,
            )

        else:
            cache.set(
                throttle_key,
                blocked_count,
                timeout=self.THROTTLE_TIMEOUT,
            )

    def log_404_event(
        self,
        request: HttpRequest,
        client_ip: str,
        blocked_count: int,
    ) -> None:
        """
        Sample logs to reduce spam during bot scans.
        """

        if blocked_count % self.LOG_SAMPLE_RATE != 0:
            return

        logger.debug(
            ("%s 404 probe detected " "client=%s " "count=%d " "path=%s"),
            self.formatted_class_name,
            client_ip,
            blocked_count,
            self.smarter_build_absolute_uri(request),
        )
