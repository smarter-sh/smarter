"""
Middleware to ensure that all requests for 'application/JSON' return responses
that are also in JSON format.
"""

import inspect
from collections.abc import Awaitable
from http import HTTPStatus

from asgiref.sync import markcoroutinefunction
from django.http import JsonResponse
from django.http.request import HttpRequest
from django.http.response import HttpResponseBase

from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins import SmarterMiddlewareMixin
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MIDDLEWARE_LOGGING])

logger.debug("Loading %s", formatted_text(__name__ + ".SmarterJsonErrorMiddleware"))


class SmarterJsonErrorMiddleware(SmarterMiddlewareMixin):
    """
    Middleware to ensure that all requests for ``application/json`` return responses
    that are also in JSON format.

    This middleware intercepts HTTP responses for requests that specify an ``Accept: application/json``
    header. If the response is an error (status code >= 400) and is not already a ``JsonResponse``,
    it wraps the error details in a JSON structure and returns a standardized JSON error response.

    This ensures that API clients and frontend applications expecting JSON always receive a
    consistent JSON error format, improving developer experience and error handling.

    **Key Features**

    - Detects requests with ``Accept: application/json``.
    - Converts non-JSON error responses (status code >= 400) to a standardized JSON format.
    - Preserves the original status code in the JSON response.
    - Integrates seamlessly with Django's middleware stack.

    .. note::
        - Only affects responses to requests that explicitly accept JSON.
        - Does not alter successful (status < 400) responses or responses already in JSON format.

    **Example**

    To enable this middleware, add it to your Django project's middleware settings::

        MIDDLEWARE = [
            ...
            'smarter.lib.django.middleware.json.SmarterJsonErrorMiddleware',
            ...
        ]

    :param request: The incoming HTTP request object.
    :type request: django.http.HttpRequest

    :param response: The outgoing HTTP response object.
    :type response: django.http.HttpResponse

    :returns: The original response, or a ``JsonResponse`` if the request expects JSON and an error occurred.
    :rtype: django.http.HttpResponse or django.http.JsonResponse

    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        self.is_async = inspect.iscoroutinefunction(get_response)
        if self.is_async:
            markcoroutinefunction(self)

    @property
    def formatted_class_name(self) -> str:
        """Return the formatted class name for logging purposes."""
        return formatted_text(f"{__name__}.{SmarterJsonErrorMiddleware.__name__}")

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:
        logger.debug("%s.__call__(): %s", self.formatted_class_name, self.smarter_build_absolute_uri(request))
        return super().__call__(request)

    def process_response(self, request, response):
        if request.headers.get("Accept") == "application/json" and response.status_code >= HTTPStatus.BAD_REQUEST:
            if not isinstance(response, JsonResponse):
                data = {
                    "error": {
                        "status_code": response.status_code,
                        "message": response.reason_phrase,
                    }
                }
                return JsonResponse(data, status=response.status_code)
        return response

    async def async_process_response(self, request, response):
        return self.process_response(request, response)
