"""Module exceptions.py"""

import logging
import re


logger = logging.getLogger(__name__)


class SmarterException(Exception):
    """Exception raised for errors in the configuration."""

    def __init__(self, message: str = ""):
        self.message = message
        msg = self.get_formatted_err_message + ": " + self.message
        logger.error(msg)
        super().__init__(self.message)

    def __str__(self):
        return self.get_formatted_err_message + ": " + self.message

    @property
    def get_formatted_err_message(self):
        words = re.findall(r"(?:[A-Z]{2,}(?=[A-Z][a-z]|[0-9]|$))|(?:[A-Z][a-z]+)", type(self).__name__)
        return " ".join(word for word in words)


class SmarterConfigurationError(SmarterException):
    """Exception raised for errors in the configuration."""


class SmarterValueError(SmarterException):
    """Exception raised for illegal or invalid values."""


class SmarterInvalidApiKeyError(SmarterException):
    """Exception raised when an invalid api key is received."""


class SmarterIlligalInvocationError(SmarterException):
    """Exception raised when the service is illegally invoked."""


class SmarterBusinessRuleViolation(SmarterException):
    """Exception raised when policies are violated."""
