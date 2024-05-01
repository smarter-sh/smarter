"""Module exceptions.py"""

from http import HTTPStatus

import openai


class SmarterExceptionBase(Exception):
    """Exception raised for errors in the configuration."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class SmarterConfigurationError(SmarterExceptionBase):
    """Exception raised for errors in the configuration."""


class SmarterValueError(SmarterExceptionBase):
    """Exception raised for illegal or invalid values."""


class SmarterIlligalInvocationError(SmarterExceptionBase):
    """Exception raised when the service is illegally invoked."""


class SmarterBusinessRuleViolation(SmarterExceptionBase):
    """Exception raised when policies are violated."""


EXCEPTION_MAP = {
    SmarterValueError: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    SmarterConfigurationError: (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError"),
    SmarterIlligalInvocationError: (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError"),
    openai.APIError: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    ValueError: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    TypeError: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    NotImplementedError: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    openai.OpenAIError: (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError"),
    Exception: (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError"),
}


def error_response_factory(e: Exception) -> dict:
    """Create a standard error response."""
    if isinstance(e, SmarterExceptionBase):
        error_class = "SmarterExceptionBase"
    else:
        error_class = "Exception"

    return {
        "errorClass": error_class,
        "stacktrace": str(e),
        "description": e.description,
        "status": e.status,
        "args": e.args,
        "cause": str(e.__cause__),
        "context": str(e.__context__),
    }
