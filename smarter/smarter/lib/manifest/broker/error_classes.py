"""
The errors that Smarter API Manifest brokers raise.

Each error names the resource kind (``thing``) and the cli command that failed, and its
:attr:`~SAMBrokerError.get_formatted_err_message` reads, e.g.,
``Smarter API Plugin manifest broker: describe() not implemented error.  <message>``.
The cli api returns the error's class name, so that a client can tell, e.g., a missing
resource from one that is not ready.
"""

from typing import ClassVar, Optional, Union

from smarter.lib.journal.enum import (
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from smarter.lib.manifest.exceptions import SAMExceptionBase


class SAMBrokerError(SAMExceptionBase):
    """
    Base class for all SAMBroker errors.

    :param message: What went wrong.
    :param thing: The resource kind, e.g. ``Plugin``.
    :param command: The cli command that failed, e.g. ``describe``.
    :param stack_trace: The stack trace, if any.
    """

    error_label: ClassVar[str] = "unidentified error"
    """The kind of error, in :attr:`get_formatted_err_message`, e.g. ``not found error``."""

    thing: Optional[Union[SmarterJournalThings, str]] = None
    command: Optional[SmarterJournalCliCommands] = None
    stack_trace: Optional[str] = None

    def __init__(
        self,
        message: Optional[str] = None,
        thing: Optional[Union[SmarterJournalThings, str]] = None,
        command: Optional[SmarterJournalCliCommands] = None,
        stack_trace: Optional[str] = None,
    ):
        self.thing = thing
        self.command = command
        self.stack_trace = stack_trace
        super().__init__(message or "")

    @property
    def get_formatted_err_message(self) -> str:
        """The error message: the thing, the command, the :attr:`error_label`, then the message, if any."""
        msg = f"Smarter API {self.thing} manifest broker: {self.command}() {self.error_label}."
        if self.message:
            msg += "  " + self.message
        return msg


class SAMBrokerReadOnlyError(SAMBrokerError):
    """Error for read-only broker operations."""

    error_label: ClassVar[str] = "read-only error"


class SAMBrokerErrorNotImplemented(SAMBrokerError):
    """Error for a broker command that the resource's broker does not implement."""

    error_label: ClassVar[str] = "not implemented error"


class SAMBrokerErrorNotReady(SAMBrokerError):
    """Error for broker operations on resources that are not ready."""

    error_label: ClassVar[str] = "not ready error"


class SAMBrokerErrorNotFound(SAMBrokerError):
    """Error for broker operations on resources that are not found."""

    error_label: ClassVar[str] = "not found error"


class SAMBrokerErrorDependencies(SAMBrokerError):
    """Error for deleting a resource that other resources depend on."""

    error_label: ClassVar[str] = "dependency error"


class SAMBrokerInternalError(SAMBrokerError):
    """Error for broker operations that result in an internal error, such as trying to create a resource that already exists."""

    error_label: ClassVar[str] = "internal error"


__all__ = [
    "SAMBrokerError",
    "SAMBrokerReadOnlyError",
    "SAMBrokerErrorNotImplemented",
    "SAMBrokerErrorNotReady",
    "SAMBrokerErrorNotFound",
    "SAMBrokerErrorDependencies",
    "SAMBrokerInternalError",
]
