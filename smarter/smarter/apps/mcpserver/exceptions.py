"""MCPServer exceptions."""

from smarter.common.exceptions import SmarterException


class SmarterMCPServerException(SmarterException):
    """Base class for all mcpserver exceptions."""

    @property
    def get_formatted_err_message(self):
        return "Smarter MCPServer error"


class SmarterMCPServerIndexError(SmarterMCPServerException):
    """A repository could not be indexed, e.g. GitHub could not be reached, or its archive is too large."""

    @property
    def get_formatted_err_message(self):
        return "Smarter MCPServer index error"


class SmarterMCPServerToolError(SmarterMCPServerException):
    """
    A tool could not do what it was asked, e.g. a file does not exist.

    The error is returned to the LLM as the tool's result, with ``isError`` set, so that it
    can correct its arguments.
    """

    @property
    def get_formatted_err_message(self):
        return "Smarter MCPServer tool error"
