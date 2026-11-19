"""
Assert how a view answers the two kinds of error that :mod:`smarter.lib.django.http.client_errors` describes.

A view that catches exceptions answers an error that the client caused, e.g. a
:class:`~django.core.exceptions.ValidationError`, with 400 and a message written for the
client. Anything else is the server's fault: the catch-all answers 500 with a fixed message,
``An unknown error occurred while ...``, and never the exception's text.

:func:`assert_reports_errors` checks both, by making one call inside the view raise::

    def test_delete_errors(self):
        url = self.url("secret_view", secret_id=self.secret.pk)
        assert_reports_errors(self, lambda: self.client.delete(url), raising(Secret, "delete"))
"""

from collections.abc import Callable
from contextlib import AbstractContextManager
from http import HTTPStatus
from typing import Optional
from unittest import TestCase
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.http import HttpResponseBase

from smarter.lib.django.http.client_errors import client_error_message

UNEXPECTED_ERROR_TEXT = "internal detail"
"""The text of the unexpected error, which the 500 response must not contain."""

UNKNOWN_ERROR_MESSAGE_PREFIX = "An unknown error occurred while"
"""The beginning of every catch-all's fixed message."""

CLIENT_ERROR_TEXT = "The name is not valid."
"""The message of the default client error, which the 400 response sends."""

ErrorPatch = Callable[[Exception], AbstractContextManager]
"""A function that takes an exception, and returns a context manager in which the view raises it."""


def response_text(response: HttpResponseBase) -> str:
    """
    Return a response's body as text.

    :param response: The response, e.g. of Django's test client, whose type declares no ``content``.
    :returns: The body, or ``""`` for a streaming response, which has no ``content``.
    """
    content: bytes = getattr(response, "content", b"")
    text = content.decode()
    return text


def raising(target: object, attribute: str) -> ErrorPatch:
    """
    Make ``target.attribute`` raise an exception, for :func:`assert_reports_errors`.

    :param target: The object, class or module whose attribute the view calls, e.g. ``Secret``.
    :param attribute: The attribute's name, e.g. ``"delete"``.
    :returns: A function that takes the exception, and returns the patch that raises it.
    """

    def patch_error(error: Exception) -> AbstractContextManager:
        return patch.object(target, attribute, side_effect=error)

    return patch_error


def assert_reports_errors(
    testcase: TestCase,
    send: Callable[[], HttpResponseBase],
    patch_error: ErrorPatch,
    client_error: Optional[Exception] = None,
) -> None:
    """
    Assert that a view answers an unexpected error with 500, and a client's error with 400.

    The request is sent twice. The first time, the patched call raises a :class:`RuntimeError`:
    the response must be a 500 whose body starts the fixed message with
    :data:`UNKNOWN_ERROR_MESSAGE_PREFIX` and doesn't contain the error's text. The second time,
    it raises ``client_error``: the response must be a 400 whose body contains the message that
    :func:`~smarter.lib.django.http.client_errors.client_error_message` gives for it. The body
    is checked as text, so a json body, with ``error``, ``detail`` or ``exception``, and a plain
    text body pass alike.

    :param testcase: The test case, for its assertions and subtests.
    :param send: A function that sends the request and returns the response.
    :param patch_error: A function that takes an exception, and returns a context manager in
        which the view raises it, e.g. ``raising(Secret, "delete")``.
    :param client_error: The client's error, a ``ValidationError`` by default.
    """
    with testcase.subTest(error="unexpected"):
        with patch_error(RuntimeError(UNEXPECTED_ERROR_TEXT)):
            response = send()
        content = response_text(response)
        testcase.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR, content[:500])
        testcase.assertNotIn(UNEXPECTED_ERROR_TEXT, content)
        testcase.assertIn(UNKNOWN_ERROR_MESSAGE_PREFIX, content)

    if client_error is None:
        client_error = ValidationError(CLIENT_ERROR_TEXT)
    expected_message = client_error_message(client_error, "")
    with testcase.subTest(error=type(client_error).__name__):
        with patch_error(client_error):
            response = send()
        content = response_text(response)
        testcase.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, content[:500])
        testcase.assertIn(expected_message, content)


__all__ = [
    "CLIENT_ERROR_TEXT",
    "UNEXPECTED_ERROR_TEXT",
    "UNKNOWN_ERROR_MESSAGE_PREFIX",
    "ErrorPatch",
    "assert_reports_errors",
    "raising",
    "response_text",
]
