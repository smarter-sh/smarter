"""
Middleware to ensure that all requests for 'application/JSON' return responses
that are also in JSON format.
"""

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class SmarterJsonErrorMiddleware(MiddlewareMixin):
    """
    Middleware to ensure that all requests for 'application/JSON' return responses
    that are also in JSON format.
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
