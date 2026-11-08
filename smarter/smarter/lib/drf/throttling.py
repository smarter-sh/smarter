"""
Request rate limits for Smarter's apis.

Smarter proxies billable LLM requests, so every api is rate limited, per
authenticated user and, for anonymous clients, per IP address. The rates are
``smarter_settings.throttle_rate_user`` and ``smarter_settings.throttle_rate_anon``,
e.g. ``600/minute``. Either can be set to ``none`` to disable it.

- **Django REST Framework views** are throttled by ``REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"]``.
- **The apis that a deployed LLMClient serves** are plain Django views, derived from
  :class:`smarter.lib.django.views.SmarterOptionallyAuthenticatedApiView`, which calls
  :func:`throttle_wait` in its ``dispatch()``.

A client that exceeds a rate receives HTTP 429 Too Many Requests, with a
``Retry-After`` header. The counters are kept in the Redis cache, through
:data:`cache_results.lazy.lazy_cache`, so that every pod shares them.
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

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


class SmarterAnonRateThrottle(AnonRateThrottle):
    """
    Limit the request rate of each anonymous client, by IP address.

    The rate is ``smarter_settings.throttle_rate_anon``. Authenticated requests are not
    limited by this throttle, but by :class:`SmarterUserRateThrottle`.
    """

    cache = lazy_cache  # type: ignore[assignment]

    def get_rate(self) -> Optional[str]:
        """
        Return the rate, e.g. ``120/minute``, or None if the throttle is disabled.

        :returns: ``smarter_settings.throttle_rate_anon``.
        """
        return smarter_settings.throttle_rate_anon


class SmarterUserRateThrottle(UserRateThrottle):
    """
    Limit the request rate of each authenticated user.

    The rate is ``smarter_settings.throttle_rate_user``. Anonymous requests are limited by
    IP address, at the same rate, and by :class:`SmarterAnonRateThrottle`.
    """

    cache = lazy_cache  # type: ignore[assignment]

    def get_rate(self) -> Optional[str]:
        """
        Return the rate, e.g. ``600/minute``, or None if the throttle is disabled.

        :returns: ``smarter_settings.throttle_rate_user``.
        """
        return smarter_settings.throttle_rate_user


CREDENTIALS_THROTTLE_RATE = "10/minute"
"""
The rate of :class:`SmarterCredentialsRateThrottle`: the number of sign-ins, sign-ups and password reset.

requests that one IP address may make. It is far below the api's general rate, because each attempt
guesses a password or sends an email.
"""


class SmarterCredentialsRateThrottle(SimpleRateThrottle):
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
        "%s.credentials_throttle_wait() throttled %s %s for %s seconds",
        logger_prefix,
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
        "%s.throttle_wait() throttled %s %s for %s seconds",
        logger_prefix,
        request.method,
        request.path,
        wait,
    )
    return max(1, int(wait))


__all__ = [
    "CREDENTIALS_THROTTLE_RATE",
    "SMARTER_THROTTLE_CLASSES",
    "SmarterAnonRateThrottle",
    "SmarterCredentialsRateThrottle",
    "SmarterUserRateThrottle",
    "credentials_throttle_wait",
    "throttle_wait",
]
