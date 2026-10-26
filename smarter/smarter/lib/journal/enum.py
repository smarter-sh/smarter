"""
The enumerations of the Smarter Journal.

The enumerations are defined in the `smarter-types <https://docs.smarter-types.smarter.sh/>`__
package, which the platform and its Python SDK share, and are re-exported here.
:class:`SmarterJournalThings` takes its kinds from
:class:`~smarter_types.kinds.SAMKinds`, which defines which kinds exist.
"""

from smarter_types import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseErrorKeys,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)

from smarter.common.exceptions import SmarterException


class SmarterJournalEnumException(SmarterException):
    """Base exception for Smarter API Manifest enumerations."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Manifest Enumeration Error"


__all__ = [
    "SCLIResponseMetadata",
    "SmarterJournalApiResponseErrorKeys",
    "SmarterJournalApiResponseKeys",
    "SmarterJournalCliCommands",
    "SmarterJournalEnumException",
    "SmarterJournalThings",
]
