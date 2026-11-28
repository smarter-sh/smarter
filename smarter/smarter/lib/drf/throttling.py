"""
Request rate limits for Smarter's apis.

Smarter proxies billable LLM requests, so every api is rate limited, per
authenticated user and, for anonymous clients, per IP address. The rates are
``smarter_settings.app_api_throttle_rate_user`` and ``smarter_settings.app_api_throttle_rate_anon``,
e.g. ``600/minute``. Either can be set to ``none`` to disable it.

- **Django REST Framework views** are throttled by ``REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"]``.
- **The apis that a deployed LLMClient serves** are plain Django views, derived from
  :class:`smarter.lib.django.views.SmarterOptionallyAuthenticatedApiView`, which calls
  :func:`throttle_wait` in its ``dispatch()``.

A client that exceeds a rate receives HTTP 429 Too Many Requests, with a
``Retry-After`` header. The counters are kept in the Redis cache, through
:data:`cache_results.lazy.lazy_cache`, so that every pod shares them. While Redis can't be reached, every throttle
lets its requests through, as :class:`SmarterCacheFailOpenThrottleMixin` explains.
"""

from typing import Optional

from cache_results import lazy_cache
from django.http import HttpRequest
from rest_framework.throttling import (
    AnonRateThrottle,
    SimpleRateThrottle,
    UserRateThrottle,
)

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.cache.exceptions import CACHE_EXCEPTIONS

logger = logging.getSmarterLogger(__name__)


class SmarterCacheFailOpenThrottleMixin:
    """
    Let a request through when the throttle's counters, in Redis, can't be read or written.

    Django REST Framework's ``SimpleRateThrottle.allow_request()`` reads and writes its cache without catching its
    errors, so during a Redis outage every throttled view, the web console's and a deployed LLMClient's included,
    would answer 500 (issue #1091). The rate limits, including :class:`SmarterCredentialsRateThrottle`'s, are
    instead off for as long as Redis is away, and each request that passes unchecked logs one warning line, as
    ``@cache_results`` computes uncached during an outage (issue #1052).
    """

    def allow_request(self, request, view) -> bool:
        """
        Check the request against the throttle, or let it through if the cache fails.

        :param request: The request.
        :param view: The view that serves the request.
        :returns: True if the request may proceed.
        """
        try:
            allowed = super().allow_request(request, view)  # type: ignore[misc]
        except CACHE_EXCEPTIONS as e:
            # one line, no traceback: Redis being away is an outage to report, not a bug to debug.
            logger.warning(
                "the cache failed, letting %s %s through %s unthrottled: %s",
                request.method,
                request.path,
                type(self).__name__,
                e,
            )
            return True
        return allowed


class SmarterAnonRateThrottle(SmarterCacheFailOpenThrottleMixin, AnonRateThrottle):
    """
    Limit the request rate of each anonymous client, by IP address.

    The rate is ``smarter_settings.app_api_throttle_rate_anon``. Authenticated requests are not
    limited by this throttle, but by :class:`SmarterUserRateThrottle`.
    """

    cache = lazy_cache  # type: ignore[assignment]

    def get_rate(self) -> Optional[str]:
        """
        Return the rate, e.g. ``120/minute``, or None if the throttle is disabled.

        :returns: ``smarter_settings.app_api_throttle_rate_anon``.
        """
        return smarter_settings.app_api_throttle_rate_anon


class SmarterUserRateThrottle(SmarterCacheFailOpenThrottleMixin, UserRateThrottle):
    """
    Limit the request rate of each authenticated user.

    The rate is ``smarter_settings.app_api_throttle_rate_user``. Anonymous requests are limited by
    IP address, at the same rate, and by :class:`SmarterAnonRateThrottle`.
    """

    cache = lazy_cache  # type: ignore[assignment]

    def get_rate(self) -> Optional[str]:
        """
        Return the rate, e.g. ``600/minute``, or None if the throttle is disabled.

        :returns: ``smarter_settings.app_api_throttle_rate_user``.
        """
        return smarter_settings.app_api_throttle_rate_user


CREDENTIALS_THROTTLE_RATE = "10/minute"
"""
The rate of :class:`SmarterCredentialsRateThrottle`: the number of sign-ins, sign-ups and password reset.

requests that one IP address may make. It is far below the api's general rate, because each attempt
guesses a password or sends an email.
"""


class SmarterCredentialsRateThrottle(SmarterCacheFailOpenThrottleMixin, SimpleRateThrottle):
    """
    Limit the rate of the actions that take a password or send an email, by IP address.

    The console's account api applies it to signing in, signing up and requesting a password reset,
    on top of the general throttles. Every such action from one address counts against the same
    limit, :data:`CREDENTIALS_THROTTLE_RATE`, so an attacker can't spread password guesses across them.
    """

    cache = lazy_cache  # type: ignore[assignment]
    scope = "credentials"

    def get_rate(self) -> Optional[str]:
        """
        Return the rate.

        :returns: :data:`CREDENTIALS_THROTTLE_RATE`.
        """
        return CREDENTIALS_THROTTLE_RATE

    def get_cache_key(self, request, view) -> str:
        """
        Return the cache key of the request's IP address.

        :param request: The request.
        :param view: The view.
        :returns: The key under which the address's attempts are counted.
        """
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


def credentials_throttle_wait(request: HttpRequest, view) -> Optional[int]:
    """
    Check a request that takes a password or sends an email against :class:`SmarterCredentialsRateThrottle`.

    :param request: The request.
    :param view: The view that serves the request.
    :returns: None if the request may proceed, or the number of seconds to wait before retrying.
    """
    throttle = SmarterCredentialsRateThrottle()
    if throttle.allow_request(request, view):  # type: ignore[arg-type]
        return None
    wait = throttle.wait()
    if wait is None:
        wait = 1
    logger.warning(
        "throttled %s %s for %s seconds",
        request.method,
        request.path,
        wait,
    )
    return max(1, int(wait))


#: The throttles of every Smarter api, in the order in which they are checked.
SMARTER_THROTTLE_CLASSES = [SmarterAnonRateThrottle, SmarterUserRateThrottle]


def throttle_wait(request: HttpRequest, view) -> Optional[int]:
    """
    Check a plain Django view's request against every Smarter throttle.

    Django REST Framework views are throttled by their ``throttle_classes``. This applies the same
    throttles, and counts against the same limits, for views that are not Django REST Framework
    views. The request's ``user`` decides which throttle applies: an authenticated user is limited
    by user, everyone else by IP address.

    :param request: The request. Its ``user`` is the authenticated user, if any.
    :param view: The view that serves the request.
    :returns: None if the request may proceed, or the number of seconds to wait before retrying.
    """
    waits = []
    for throttle_class in SMARTER_THROTTLE_CLASSES:
        throttle = throttle_class()
        if not throttle.allow_request(request, view):  # type: ignore[arg-type]
            waits.append(throttle.wait())
    if not waits:
        return None
    # a throttle's wait() is None when it can't say how long to wait.
    known_waits = []
    for throttle_wait_seconds in waits:
        if throttle_wait_seconds is not None:
            known_waits.append(throttle_wait_seconds)
    wait = max(known_waits, default=1)
    logger.warning(
        "throttled %s %s for %s seconds",
        request.method,
        request.path,
        wait,
    )
    return max(1, int(wait))


__all__ = [
    "CREDENTIALS_THROTTLE_RATE",
    "SMARTER_THROTTLE_CLASSES",
    "SmarterAnonRateThrottle",
    "SmarterCacheFailOpenThrottleMixin",
    "SmarterCredentialsRateThrottle",
    "SmarterUserRateThrottle",
    "credentials_throttle_wait",
    "throttle_wait",
]
