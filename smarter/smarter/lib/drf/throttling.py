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
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from smarter.common.conf import smarter_settings
from smarter.lib import logging

logger = logging.getLogger(__name__)


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
    wait = max((w for w in waits if w is not None), default=1)
    logger.warning(
        "%s.throttle_wait() throttled %s %s for %s seconds",
        __name__,
        request.method,
        request.path,
        wait,
    )
    return max(1, int(wait))


__all__ = ["SMARTER_THROTTLE_CLASSES", "SmarterAnonRateThrottle", "SmarterUserRateThrottle", "throttle_wait"]
