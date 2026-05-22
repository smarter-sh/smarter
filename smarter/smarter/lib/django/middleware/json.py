"""
Middleware that guarantees JSON-formatted error responses for clients
requesting JSON content.

This middleware intercepts non-JSON error responses and converts them
into standardized ``JsonResponse`` objects when the client explicitly
indicates JSON support through HTTP content negotiation headers.

Key Features
============

- Converts non-JSON error responses into JSON
- Preserves original HTTP status codes
- Supports sync and async Django execution
- Performs HTTP Accept-header content negotiation
- Leaves successful responses untouched
- Preserves existing JSON responses
- Feature-flag enablement via Django Waffle

Behavior
========

For each response, the middleware:

#. Determines whether the client accepts JSON responses
#. Detects whether the response represents an error condition
#. Detects whether the response is already JSON
#. Converts eligible error responses into ``JsonResponse`` objects
#. Preserves the original HTTP status code

Only error responses are normalized.

Responses with status codes below ``400 Bad Request`` are returned
unchanged.

Content Negotiation
===================

The middleware performs lightweight content negotiation using the
request ``Accept`` header.

JSON normalization is enabled only when the client advertises support
for one of the configured JSON content types.

Supported JSON content types include:

- ``application/json``
- ``application/problem+json``

Error Payload Format
====================

Normalized JSON responses use the following structure:

.. code-block:: json

   {
     "error": {
       "status_code": 404,
       "message": "Not Found"
     }
   }

The payload preserves:

- the original HTTP status code
- the original HTTP reason phrase

Async Compatibility
===================

The middleware supports both synchronous and asynchronous Django
execution models.

Coroutine-based request handlers are detected automatically during
middleware initialization.

Async request execution delegates synchronous middleware processing
through ``sync_to_async()`` to preserve compatibility with Django's
middleware lifecycle.

Response Handling Rules
=======================

The middleware intentionally avoids modifying:

- successful responses
- existing JSON responses
- clients not requesting JSON content

This ensures compatibility with:

- HTML browser workflows
- Django admin
- traditional server-rendered views
- API clients expecting structured JSON errors

Feature Flags
=============

Middleware activation is controlled using Django Waffle:

- ``ENABLE_MIDDLEWARE_SMARTER_JSON_ERROR``

When disabled, the middleware behaves as a transparent pass-through.

Logging
=======

The middleware emits structured logs for:

- middleware initialization
- request processing
- JSON error normalization events

Classes
=======

.. autosummary::
   :toctree: generated/

   SmarterJsonErrorMiddleware

Dependencies
============

- Django
- asgiref
- Django Waffle

Warnings
========

This middleware performs lightweight content negotiation based solely
on ``Accept`` headers and does not implement full RFC-compliant
negotiation semantics.

Clients advertising wildcard media types without explicit JSON support
may not receive normalized JSON errors.

Notes
=====

This middleware depends on helper functionality provided by
:class:`smarter.common.mixins.SmarterMiddlewareMixin`.

The middleware preserves Django response semantics by avoiding
modification of successful responses and preserving original HTTP
status codes during normalization.
"""

from __future__ import annotations

from collections.abc import Awaitable
from http import HTTPStatus

from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.http.request import HttpRequest
from django.http.response import HttpResponseBase

from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin, SmarterMiddlewareMixin
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__)

if waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SMARTER_JSON_ERROR):
    logger.debug(
        "%s is %s",
        formatted_text(__name__ + ".SmarterJsonErrorMiddleware"),
        SmarterHelperMixin().formatted_state_ready,
    )
else:
    logger.debug(
        "%s is %s. Enable with Django waffle in the admin console.",
        formatted_text(__name__ + ".SmarterJsonErrorMiddleware"),
        SmarterHelperMixin().formatted_state_not_ready,
    )


class SmarterJsonErrorMiddleware(SmarterMiddlewareMixin):
    """
    Middleware that converts non-JSON error responses into JSON responses
    for clients requesting JSON content.
    """

    JSON_CONTENT_TYPES = (
        "application/json",
        "application/problem+json",
    )

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:

        if self.async_mode:
            return self.__acall__(request)

        if self.deserves_amnesty(request.path):
            return self.get_response(request)

        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SMARTER_JSON_ERROR):
            return self.get_response(request)

        logger.debug("%s.__call__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)
        response = self.get_response(request)
        response = self.process_response(request, response)

        return response

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:

        if not await waffle.async_switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SMARTER_JSON_ERROR):
            return await sync_to_async(self.get_response)(request)

        logger.debug("%s.__acall__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)
        response = await sync_to_async(self.get_response)(request)
        response = await self.async_process_response(request, response)

        return response

    @property
    def formatted_class_name(self) -> str:
        return formatted_text(f"{__name__}.{self.__class__.__name__}[{id(self)}]")

    def process_response(self, request: HttpRequest, response: HttpResponseBase) -> HttpResponseBase:

        if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SMARTER_JSON_ERROR):
            return response

        return self.normalize_json_error_response(request=request, response=response)

    async def async_process_response(self, request: HttpRequest, response: HttpResponseBase) -> HttpResponseBase:

        if not await waffle.async_switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SMARTER_JSON_ERROR):
            return response

        return await sync_to_async(self.normalize_json_error_response)(request=request, response=response)

    def normalize_json_error_response(self, request: HttpRequest, response: HttpResponseBase) -> HttpResponseBase:
        """
        Convert non-JSON error responses into JsonResponse objects.
        """

        if not self.client_accepts_json(request):
            return response

        if response.status_code < HTTPStatus.BAD_REQUEST:
            return response

        if self.response_is_json(response):
            return response

        logger.debug(
            "%s converting non-json error response status=%d",
            self.formatted_class_name,
            response.status_code,
        )

        payload = self.build_error_payload(response)

        return JsonResponse(payload, status=response.status_code)

    def client_accepts_json(self, request: HttpRequest) -> bool:
        """
        Determine whether the client accepts JSON responses.
        """

        accept_header = request.headers.get("Accept", "").lower()

        if not accept_header:
            return False

        return any(content_type in accept_header for content_type in self.JSON_CONTENT_TYPES)

    @staticmethod
    def response_is_json(response: HttpResponseBase) -> bool:
        """
        Detect whether the response is already JSON.
        """

        content_type = response.get(
            "Content-Type",
            "",
        ).lower()
        return "json" in content_type

    @staticmethod
    def build_error_payload(response: HttpResponseBase) -> dict:
        """
        Build standardized JSON error payload.
        """

        return {
            "error": {
                "status_code": response.status_code,
                "message": response.reason_phrase,
            }
        }
