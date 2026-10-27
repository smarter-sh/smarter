"""Module exceptions.py."""

import re

from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


class SmarterException(Exception):
    """
    Base class of Smarter's exceptions.

    Constructing an exception logs it at DEBUG only. Many are raised, then caught and handled as an
    expected outcome, e.g. a manifest that names a Secret that doesn't exist, which ``load_from_github``
    skips. The code that handles an exception logs it, at the level that the outcome deserves.
    """

    def __init__(self, message: str = ""):
        self.message = message
        logger.debug(
            "%s.SmarterException.__init__() %s: %s", logger_prefix, self.get_formatted_err_message, self.message
        )
        super().__init__(self.message)

    def __str__(self) -> str:
        """
        The error label, followed by the message.

        Some subclasses, e.g. the manifest broker errors, already include the message in their
        label; it is not repeated.

        :returns: ``"<label>: <message>"``, or the label alone when it already contains the message.
        """
        label = self.get_formatted_err_message
        if self.message and self.message in label:
            return label
        return label + ": " + self.message

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
