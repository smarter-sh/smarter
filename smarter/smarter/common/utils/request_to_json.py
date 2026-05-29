"""
smarter.common.utils.request_to_json
====================================

Utility for converting Django ASGIRequest objects to JSON-serializable dictionaries.

This module provides the ``request_to_json`` function, which extracts relevant information from a Django
ASGIRequest object (such as HTTP method, URL, and JSON body) and returns it as a dictionary suitable for
serialization. If a dictionary or list is provided, it is returned as-is.

**Example usage:**

.. code-block:: python

    from smarter.common.utils import request_to_json
    from django.core.handlers.asgi import ASGIRequest

    # Example with ASGIRequest
    request = ASGIRequest(...)
    data = request_to_json(request)
    print(data)

    # Example with dictionary
    data = request_to_json({"foo": "bar"})
    print(data)  # Output: {'foo': 'bar'}

"""

from typing import Any, Optional, TypedDict, Union

from django.core.handlers.asgi import ASGIRequest

from smarter.common.exceptions import SmarterValueError
from smarter.lib import json


class RequestData(TypedDict):
    """
    TypedDict representing the relevant data extracted from a request object.
    """

    method: str
    url: str
    body: Optional[Union[dict[str, Any], list[Any]]]


def request_to_json(request: ASGIRequest | dict | list) -> Union[RequestData, ASGIRequest, dict, list]:
    """
    Convert a Django ASGIRequest object, dictionary, or list to a JSON-serializable dictionary or list.

    This function is primarily intended to extract relevant information from a Django ASGIRequest object
    (such as HTTP method, URL, and JSON body) and return it as a dictionary suitable for serialization.
    If a dictionary or list is provided, it is returned as-is.

    :param request: The request object to convert. Can be a Django ASGIRequest, a dictionary, or a list.
    :type request: ASGIRequest | dict | list

    :return: A JSON-serializable dictionary or list representing the request data.
    :rtype: dict[str, Any] | list[Any]

    .. note::
        - If the request is an ASGIRequest, the function attempts to decode and parse the request body as JSON.
        - If the body cannot be parsed as JSON, the 'body' field will be set to None.
        - If the input is already a dictionary or list, it is returned unchanged.

    **Example usage:**

    .. code-block:: python

        from smarter.common.utils import request_to_json
        from django.core.handlers.asgi import ASGIRequest

        # Example with ASGIRequest
        request = ASGIRequest(...)
        data = request_to_json(request)
        print(data)

        # Example with dictionary
        data = request_to_json({"foo": "bar"})
        print(data)  # Output: {'foo': 'bar'}

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

        return {
            "method": request.method,
            "url": request.build_absolute_uri(),
            "body": body_json,
        }
    elif isinstance(request, (dict, list)):
        return request

    raise SmarterValueError(f"Unsupported request type: {type(request)}. Expected ASGIRequest, dict, or list.")


__all__ = ["RequestData", "request_to_json"]
