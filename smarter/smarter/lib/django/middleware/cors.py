"""
CORS middleware that runs ``django-cors-headers`` behind a waffle switch, in sync and async mode.

This module extends :class:`corsheaders.middleware.CorsMiddleware`. It adds no CORS logic of its
own: which origins are allowed, including regex matches, is decided by ``django-cors-headers``
from the ``CORS_*`` Django settings, e.g. ``CORS_ALLOWED_ORIGINS`` and
``CORS_ALLOWED_ORIGIN_REGEXES``. The local settings add the localhost origins there.

Behavior
========

For each request, the middleware:

#. In sync mode, passes an amnesty path (see
   :meth:`smarter.common.mixins.SmarterHelperMixin.deserves_amnesty`) straight to the next handler
#. Passes the request straight to the next handler when the ``ENABLE_MIDDLEWARE_CORS`` switch is off
#. Otherwise, defers to ``django-cors-headers``, which adds the CORS headers

Async Compatibility
===================

The middleware detects a coroutine-based next handler when it is created, and then runs
:meth:`SmarterCorsMiddleware.__acall__` for every request. It keeps no request state on the
instance, which every request shares.

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
"""

from __future__ import annotations

from collections.abc import Awaitable
from functools import cached_property
from inspect import isawaitable, iscoroutinefunction

from asgiref.sync import markcoroutinefunction
from corsheaders.middleware import CorsMiddleware
from django.http import HttpRequest, HttpResponseBase

from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MIDDLEWARE_LOGGING])
if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CORS):
    logger.debug(
        "%s is %s",
        logging.SmarterFormattedText.text(__name__) + ".SmarterCorsMiddleware",
        SmarterHelperMixin().formatted_state_ready,
    )
else:
    logger.debug(
        "%s is %s. Enable with Django waffle in the admin console.",
        logging.SmarterFormattedText.text(__name__) + ".SmarterCorsMiddleware",
        SmarterHelperMixin().formatted_state_not_ready,
    )


class SmarterCorsMiddleware(CorsMiddleware, SmarterHelperMixin):
    """
    CORS middleware that applies ``django-cors-headers`` only while ``ENABLE_MIDDLEWARE_CORS`` is on.

    **Design rules:**

    - no shared request state on self
    - no coroutine guessing in core logic
    - one class for sync and async mode

    The allowed origins come from the ``CORS_*`` Django settings, through
    :class:`corsheaders.middleware.CorsMiddleware`. In sync mode, an amnesty path skips the
    middleware too.

    **Example**

    To enable this middleware, add it to your Django project's middleware settings::

        MIDDLEWARE = [
            ...
            'smarter.lib.django.middleware.cors.SmarterCorsMiddleware',
            ...
        ]
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        """
        Initialize ``django-cors-headers``, and detect whether the next handler is async.

        :param get_response: The next handler in the middleware chain.
        """
        super().__init__(get_response)

        self.get_response = get_response
        self.async_mode = iscoroutinefunction(get_response)

        if self.async_mode:
            markcoroutinefunction(self)

    @cached_property
    def formatted_class_name(self) -> str:
        """Return the formatted class name for logging purposes.

        It names the instance, not a request.
        """
        class_name = f"{__name__}.{SmarterCorsMiddleware.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:
        """
        Add CORS headers to a sync response, or hand the request to :meth:`__acall__` in async mode.

        An amnesty path, or a request while ``ENABLE_MIDDLEWARE_CORS`` is off, gets the next
        handler's response unchanged.

        :param request: The incoming request.
        :returns: The response (a coroutine in async mode).
        """
        if self.async_mode:
            return self.__acall__(request)

        if self.deserves_amnesty(request.path):
            return self.get_response(request)

        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CORS):
            return self.get_response(request)

        return super().__call__(request)

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        """
        Add CORS headers to an async response, unless ``ENABLE_MIDDLEWARE_CORS`` is off.

        Unlike :meth:`__call__`, it does not check for an amnesty path.

        :param request: The incoming request.
        :returns: The response.
        """
        if not await waffle.async_switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CORS):
            result = self.get_response(request)
            if isawaitable(result):
                return await result
            return result

        return await super().__acall__(request)
