"""
Exceptions of the MCPServer app.

:class:`SmarterMCPServerException` is the base of every exception that the app raises. The two
kinds that callers handle are:

- :class:`SmarterMCPServerIndexError`, when a repository or the blog cannot be indexed. The
  indexer records it in the index's ``error``, rather than failing its Celery task.
- :class:`SmarterMCPServerToolError`, when a tool cannot do what it was asked. The MCP server
  returns it to the LLM as the tool's result, rather than as a JSON-RPC error.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.common.exceptions import SmarterException


class SmarterMCPServerException(SmarterException):
    """
    Base class of every exception of the MCPServer app.

    Catch it to handle any of the app's errors. Raise one of its subclasses, which say what
    failed.
    """

    @property
    def get_formatted_err_message(self) -> str:
        """
        Return the title of the error, as the platform's error responses show it.

        :returns: ``"Smarter MCPServer error"``.
        """
        return "Smarter MCPServer error"


class SmarterMCPServerIndexError(SmarterMCPServerException):
    """
    A repository could not be indexed, e.g. GitHub could not be reached, or its archive is too large.

    When GitHub or the blog fails, the indexer catches it, records its message in the index's
    ``error`` and sends ``mcpserver_repository_index_failed``, so that the previous index, if
    any, is still searched. Only a repository name that is not one of The Smarter Project's
    reaches the caller.
    """

    @property
    def get_formatted_err_message(self) -> str:
        """
        Return the title of the error, as the platform's error responses show it.

        :returns: ``"Smarter MCPServer index error"``.
        """
        return "Smarter MCPServer index error"


class SmarterMCPServerToolError(SmarterMCPServerException):
    """
    A tool could not do what it was asked, e.g. a file does not exist.

    The error is returned to the LLM as the tool's result, with ``isError`` set, so that it
    can correct its arguments. Because a tool raises it, rather than returning the message, a
    failed tool call is never cached (see :mod:`smarter.apps.mcpserver.caching`).
    """

    @property
    def get_formatted_err_message(self) -> str:
        """
        Return the title of the error, as the platform's error responses show it.

        :returns: ``"Smarter MCPServer tool error"``.
        """
        return "Smarter MCPServer tool error"
