"""
Middleware to ensure that all requests for 'application/JSON' return responses
that are also in JSON format.
"""

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class SmarterJsonErrorMiddleware(MiddlewareMixin):
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

    def process_response(self, request, response):
        if request.headers.get("Accept") == "application/json" and response.status_code >= 400:
            if not isinstance(response, JsonResponse):
                data = {
                    "error": {
                        "status_code": response.status_code,
                        "message": response.reason_phrase,
                    }
                }
                return JsonResponse(data, status=response.status_code)
        return response
