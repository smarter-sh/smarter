"""Custom exceptions for Smarter API Manifest handling."""

import re

from smarter.common.exceptions import SmarterException


class SAMExceptionBase(SmarterException):
    """Base exception for Smarter API Manifest handling."""

    @property
    def get_formatted_err_message(self):
        name = self.__class__.__name__
        name = name.replace("SAM", "Smarter API Manifest ")
        words = re.findall("[A-Z][^A-Z]*", name)
        retval = " ".join(str(word).lower() for word in words)
        return retval.replace("smarter  a p i  manifest", "Smarter API Manifest").replace("  ", " ")


class SAMBadRequestError(SAMExceptionBase):
    """Exception raised when handling http requests."""


class SAMValidationError(SAMExceptionBase):
    """Exception raised during Plugin validation."""
