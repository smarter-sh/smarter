"""
Narrow the loosely typed values that tests inspect, so that type checkers see what each test expects.

mypy (with ``check_untyped_defs``) and pyright check the bodies of tests, and refuse e.g. ``body["data"]`` on a
value typed as JSON, which may be a list, a string or None, or ``response.content`` on a value typed as
``HttpResponseBase | Awaitable[HttpResponseBase]``. Each function returns its argument, narrowed, or fails the
test with a clear message if it is not what the test expected:

.. code-block:: python

    from smarter.lib.unittest.narrowing import http_response, json_object

    data = json_object(response.json())["data"]
    self.assertEqual(http_response(middleware(request)).content, b"ok")

For an Optional value, use ``assert value is not None`` in a test, or :func:`smarter.lib.typing.required`.
"""

from typing import Any

from django.http import HttpResponse

from smarter.lib.typing import SmarterDictType


def json_object(value: object, name: str = "value") -> SmarterDictType:
    """
    Return a JSON value that the test expects to be an object, as a dict.

    :param value: The value, e.g. a parsed response body.
    :param name: The value's name, for the failure's message.
    :returns: The value.
    :raises AssertionError: If the value is not a dict.
    """
    if not isinstance(value, dict):
        raise AssertionError(f"{name} is not a JSON object, but {type(value).__name__}: {str(value)[:200]}")
    return value


def json_list(value: object, name: str = "value") -> list[Any]:
    """
    Return a JSON value that the test expects to be an array, as a list.

    :param value: The value, e.g. a response's ``objects``.
    :param name: The value's name, for the failure's message.
    :returns: The value.
    :raises AssertionError: If the value is not a list.
    """
    if not isinstance(value, list):
        raise AssertionError(f"{name} is not a JSON array, but {type(value).__name__}: {str(value)[:200]}")
    return value


def http_response(response: object) -> HttpResponse:
    """
    Return a response that the test expects to be a complete ``HttpResponse``, with ``content``.

    A view, a middleware or a decorated function is typed to return ``HttpResponseBase``, or an awaitable of
    one, though a synchronous call returns an ``HttpResponse``.

    :param response: The response.
    :returns: The response.
    :raises AssertionError: If it is not an ``HttpResponse``, e.g. an un-awaited coroutine or a streaming
        response.
    """
    if not isinstance(response, HttpResponse):
        raise AssertionError(f"the response is not an HttpResponse, but {type(response).__name__}")
    return response


__all__ = ["http_response", "json_list", "json_object"]
