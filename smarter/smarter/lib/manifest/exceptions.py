"""Custom exceptions for Smarter API Manifest handling."""

import re

from smarter.common.exceptions import SmarterExceptionBase


class SAMExceptionBase(SmarterExceptionBase):
    """Base exception for Smarter API Manifest handling."""

    @property
    def get_readable_name(self):
        name = self.__class__.__name__
        name = name.replace("SAM", "Smarter API Manifest ")
        words = re.findall("[A-Z][^A-Z]*", name)
        return " ".join(word for word in words)


class SAMBadRequestError(SAMExceptionBase):
    """Exception raised when handling http requests."""


class SAMValidationError(SAMExceptionBase):
    """Exception raised during Plugin validation."""
