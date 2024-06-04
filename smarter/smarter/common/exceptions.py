"""Module exceptions.py"""

import logging
import re


logger = logging.getLogger(__name__)


class SmarterExceptionBase(Exception):
    """Exception raised for errors in the configuration."""

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.get_formatted_err_message + ": " + self.message

    @property
    def get_formatted_err_message(self):
        words = re.findall("[A-Z][^A-Z]*", type(self).__name__)
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
