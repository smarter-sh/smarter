"""Module exceptions.py"""

import re


class SmarterExceptionBase(Exception):
    """Exception raised for errors in the configuration."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.get_readable_name + ": " + self.message

    @property
    def get_readable_name(self):
        words = re.findall("[A-Z][^A-Z]*", self.__name__)
        return " ".join(word for word in words)


class SmarterConfigurationError(SmarterExceptionBase):
    """Exception raised for errors in the configuration."""


class SmarterValueError(SmarterExceptionBase):
    """Exception raised for illegal or invalid values."""


class SmarterInvalidApiKeyError(SmarterExceptionBase):
    """Exception raised when an invalid api key is received."""


class SmarterIlligalInvocationError(SmarterExceptionBase):
    """Exception raised when the service is illegally invoked."""


class SmarterBusinessRuleViolation(SmarterExceptionBase):
    """Exception raised when policies are violated."""


def error_response_factory(e: Exception) -> dict:
    """Create a standard error response."""
    if isinstance(e, SmarterExceptionBase):
        error_class = "SmarterExceptionBase"
    else:
        error_class = "Exception"

    return {
        "errorClass": error_class,
        "stacktrace": str(e),
        "description": e.args[0] if e.args else "",  # get the error message from args
        "status": e.status if hasattr(e, "status") else "",  # check if status attribute exists
        "args": e.args,
        "cause": str(e.__cause__),
        "context": str(e.__context__),
    }
