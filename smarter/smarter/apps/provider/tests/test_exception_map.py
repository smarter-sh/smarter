"""Test :func:`smarter.apps.provider.services.text_completion.lib.exception_map.exception_status_and_message`."""

from http import HTTPStatus

import httpx
import openai

from smarter.apps.provider.services.text_completion.lib.exception_map import (
    exception_status_and_message,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib.unittest.base_classes import SmarterTestBase

REQUEST = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


def provider_error(error_class: type[openai.APIStatusError], status: int, body) -> openai.APIStatusError:
    """An error response from the LLM provider, as the openai client raises it."""
    return error_class("the openai client's message", response=httpx.Response(status, request=REQUEST), body=body)


class TestExceptionStatusAndMessage(SmarterTestBase):
    """Test that a prompt's error keeps the LLM provider's status and message."""

    def test_provider_errors_keep_their_status_and_message(self):
        cases = [
            # the openai client passes the "error" object of the response body
            (
                provider_error(
                    openai.NotFoundError,
                    404,
                    {"message": "The model `gpt-9` does not exist or you do not have access to it."},
                ),
                HTTPStatus.NOT_FOUND,
                "The model `gpt-9` does not exist or you do not have access to it.",
            ),
            (
                provider_error(
                    openai.BadRequestError,
                    400,
                    {"error": {"message": "Unsupported value: 'temperature' does not support 0.2 with this model."}},
                ),
                HTTPStatus.BAD_REQUEST,
                "Unsupported value: 'temperature' does not support 0.2 with this model.",
            ),
            (
                provider_error(openai.RateLimitError, 429, {"message": "Rate limit reached."}),
                HTTPStatus.TOO_MANY_REQUESTS,
                "Rate limit reached.",
            ),
            # a body without a message falls back to the openai client's message
            (
                provider_error(openai.InternalServerError, 503, None),
                HTTPStatus.SERVICE_UNAVAILABLE,
                "the openai client's message",
            ),
        ]
        for e, status, message in cases:
            with self.subTest(error=type(e).__name__):
                self.assertEqual(exception_status_and_message(e), (status, message))

    def test_connection_errors(self):
        status, message = exception_status_and_message(openai.APITimeoutError(request=REQUEST))
        self.assertEqual(status, HTTPStatus.GATEWAY_TIMEOUT)
        self.assertIn("did not respond in time", message)
        status, message = exception_status_and_message(openai.APIConnectionError(request=REQUEST))
        self.assertEqual(status, HTTPStatus.BAD_GATEWAY)
        self.assertIn("Could not connect", message)

    def test_other_errors_are_mapped_by_class(self):
        class SubclassOfSmarterValueError(SmarterValueError):
            """A subclass, which is mapped by its base class."""

        self.assertEqual(exception_status_and_message(SubclassOfSmarterValueError("bad"))[0], HTTPStatus.BAD_REQUEST)
        self.assertEqual(exception_status_and_message(RuntimeError("bug")), (HTTPStatus.INTERNAL_SERVER_ERROR, "bug"))
