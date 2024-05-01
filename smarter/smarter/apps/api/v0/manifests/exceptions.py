"""Custom exceptions for Smarter API Manifest handling."""

from smarter.common.exceptions import SmarterExceptionBase


class SAMValidationError(SmarterExceptionBase):
    """Exception raised during Plugin validation."""
