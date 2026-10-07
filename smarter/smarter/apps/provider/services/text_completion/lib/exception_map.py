"""
Mapping of exceptions to HTTP status codes and error types for prompt providers.

This is used in the main try block of handler() to map exceptions to
HTTP status codes and error types.
"""

from http import HTTPStatus

import openai

from smarter.common.exceptions import (
    SmarterConfigurationError,
    SmarterIlligalInvocationError,
    SmarterValueError,
)
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

# 1.) EXCEPTION_MAP: A dictionary that maps exceptions to HTTP status codes and error types.
# Base exception map for prompt providers. This maps internally raised exceptions to HTTP status codes.
BASE_EXCEPTION_MAP = {
    SmarterValueError: (HTTPStatus.BAD_REQUEST.value, "BadRequest"),
    SmarterConfigurationError: (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError"),
    SmarterIlligalInvocationError: (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError"),
    ValueError: (HTTPStatus.BAD_REQUEST.value, "BadRequest"),
    TypeError: (HTTPStatus.BAD_REQUEST.value, "BadRequest"),
    NotImplementedError: (HTTPStatus.BAD_REQUEST.value, "BadRequest"),
    Exception: (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError"),
}

EXCEPTION_MAP = BASE_EXCEPTION_MAP.copy()
EXCEPTION_MAP[openai.APIError] = (HTTPStatus.BAD_REQUEST.value, "BadRequestError")
EXCEPTION_MAP[openai.OpenAIError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.ConflictError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.NotFoundError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.APIStatusError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.RateLimitError] = (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "InternalServerError")
EXCEPTION_MAP[openai.APITimeoutError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.BadRequestError] = (HTTPStatus.BAD_REQUEST.value, "BadRequestError")
EXCEPTION_MAP[openai.APIConnectionError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.AuthenticationError] = (HTTPStatus.UNAUTHORIZED.value, "UnauthorizedError")
EXCEPTION_MAP[openai.InternalServerError] = (HTTPStatus.INTERNAL_SERVER_ERROR.value, "InternalServerError")
EXCEPTION_MAP[openai.PermissionDeniedError] = (HTTPStatus.UNAUTHORIZED.value, "UnauthorizedError")
EXCEPTION_MAP[openai.LengthFinishReasonError] = (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "RequestEntityTooLargeError")
EXCEPTION_MAP[openai.UnprocessableEntityError] = (HTTPStatus.BAD_REQUEST.value, "BadRequestError")
EXCEPTION_MAP[openai.APIResponseValidationError] = (HTTPStatus.BAD_REQUEST.value, "BadRequestError")
EXCEPTION_MAP[openai.ContentFilterFinishReasonError] = (HTTPStatus.BAD_REQUEST.value, "BadRequestError")
"""Used in the main try block of handler() to map exceptions to HTTP status codes and error types."""


def provider_error_message(e: openai.APIStatusError) -> str:
    """The error message in the LLM provider's response, e.g. "The model `gpt-9` does not exist"."""
    body = e.body
    if isinstance(body, dict):
        error = body.get("error", body)
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(body.get("message"), str):
            return body["message"]
    return e.message


def exception_status_and_message(e: BaseException) -> tuple[int, str]:
    """
    The HTTP status and the error message of a prompt that raised the exception.

    An error response from the LLM provider, e.g. a 400 or a 404 from api.openai.com, keeps the
    provider's status and message, so that the client sees what the provider said. Any other
    exception is mapped by its class, including its base classes, in EXCEPTION_MAP.
    """
    if isinstance(e, openai.APIStatusError):
        return int(e.status_code), provider_error_message(e)
    if isinstance(e, openai.APITimeoutError):
        return HTTPStatus.GATEWAY_TIMEOUT.value, f"The LLM provider did not respond in time: {e}"
    if isinstance(e, openai.APIConnectionError):
        return HTTPStatus.BAD_GATEWAY.value, f"Could not connect to the LLM provider: {e}"
    for cls in type(e).__mro__:
        if cls in EXCEPTION_MAP:
            return int(EXCEPTION_MAP[cls][0]), str(e)
    return HTTPStatus.INTERNAL_SERVER_ERROR.value, str(e)


__all__ = ["EXCEPTION_MAP", "exception_status_and_message"]
