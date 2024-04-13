"""Module exceptions.py"""

from http import HTTPStatus

import openai


class SmarterConfigurationError(Exception):
    """Exception raised for errors in the configuration."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class SmarterValueError(Exception):
    """Exception raised for errors in the configuration."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class SmarterIlligalInvocationError(Exception):
    """Exception raised when the service is called by an unknown service."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


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
