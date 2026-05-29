"""
Utility function to convert a Django request object to a JSON-serializable dictionary.
"""

from typing import Any, Union

from django.core.handlers.asgi import ASGIRequest

from smarter.lib import json


def request_to_json(request: ASGIRequest | dict | list) -> Union[dict[str, Any], list[Any]]:
    """
    Convert a Django request object to a JSON-serializable dictionary.
    """

    if isinstance(request, ASGIRequest):
        body_str = request.body.decode("utf-8") if request.body else None
        body_json = None
        if body_str:
            try:
                parsed = json.loads(body_str)
                if isinstance(parsed, str):
                    body_json = json.loads(parsed)
                else:
                    body_json = parsed
            except (json.JSONDecodeError, TypeError):
                body_json = None

        request_data = {
            "method": request.method,
            "url": request.build_absolute_uri(),
            "body": body_json,
        }
    else:
        request_data = request

    return request_data


__all__ = ["request_to_json"]
