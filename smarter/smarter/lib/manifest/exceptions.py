"""Custom exceptions for Smarter API Manifest handling."""

from smarter.common.exceptions import SmarterExceptionBase


class SAMBadRequestError(SmarterExceptionBase):
    """Exception raised when handling http requests."""


class SAMValidationError(SmarterExceptionBase):
    """Exception raised during Plugin validation."""
