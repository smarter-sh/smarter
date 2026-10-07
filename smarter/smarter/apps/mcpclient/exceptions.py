"""MCPClient exceptions."""

from smarter.common.exceptions import SmarterException


class SmarterMCPClientException(SmarterException):
    """Base class for all mcpclient exceptions."""

    @property
    def get_formatted_err_message(self):
        return "Smarter MCPClient error"


class SmarterMCPClientConfigurationError(SmarterMCPClientException):
    """An MCPClient is not configured correctly, e.g. its credentials Secret is missing."""

    @property
    def get_formatted_err_message(self):
        return "Smarter MCPClient configuration error"


class SmarterMCPClientConnectionError(SmarterMCPClientException):
    """Smarter could not connect to an MCP server, or the server did not respond correctly."""

    @property
    def get_formatted_err_message(self):
        return "Smarter MCPClient connection error"


class SmarterMCPClientPermissionError(SmarterMCPClientException):
    """A tool or resource is not allowed by an MCPClient's allowedTools or allowedResources."""

    @property
    def get_formatted_err_message(self):
        return "Smarter MCPClient permission error"
