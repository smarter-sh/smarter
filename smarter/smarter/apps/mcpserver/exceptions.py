"""
Exceptions of the MCPServer app.

:class:`SmarterMCPServerException` is the base of every exception that the app raises. The two
kinds that callers handle are:

- :class:`SmarterMCPServerIndexError`, when a repository or the blog cannot be indexed. The
  indexer records it in the index's ``error``, rather than failing its Celery task.
- :class:`SmarterMCPServerServiceError`, when a service of :mod:`smarter.apps.mcpserver.services`
  cannot do what it was asked, e.g. read a file that does not exist. Its message is written for
  the caller, so that they can correct the request. :class:`SmarterMCPServerNotFoundError`
  adds what the caller may have meant.
- :class:`SmarterMCPServerToolError`, when a tool cannot do what it was asked. The MCP server
  returns it to the LLM as the tool's result, rather than as a JSON-RPC error. The tools of
  :mod:`smarter.apps.mcpserver.protocol.tools` turn a service error into one.

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


class SmarterMCPServerServiceError(SmarterMCPServerException):
    """
    A service could not do what it was asked, e.g. a file does not exist, or a repository is not indexed yet.

    The services of :mod:`smarter.apps.mcpserver.services` raise it, with a message that tells the
    caller what was wrong, and what to do instead, e.g. "Did you mean: ...?". They know nothing of
    MCP: :meth:`smarter.apps.mcpserver.protocol.tools.public.PublicTool.call` and
    :meth:`smarter.apps.mcpserver.protocol.tools.staff.StaffTool.call` turn it into a
    :class:`SmarterMCPServerToolError`, which the LLM reads as the tool's result.
    """

    @property
    def get_formatted_err_message(self) -> str:
        """
        Return the title of the error, as the platform's error responses show it.

        :returns: ``"Smarter MCPServer service error"``.
        """
        return "Smarter MCPServer service error"


class SmarterMCPServerNotFoundError(SmarterMCPServerServiceError):
    """
    A file, folder or blog post that was asked for does not exist, with what the caller may have meant.

    :param message: What was not found, and, when there are suggestions, "Did you mean: ...?".
    :param suggestions: The paths that the caller may have meant, best first, or an empty list.
    """

    def __init__(self, message: str, suggestions: list[str]):
        """
        Keep the suggestions, so that the caller can say how to find the item when there are none.

        :param message: What was not found, with the suggestions, if any.
        :param suggestions: The paths that the caller may have meant.
        """
        self.suggestions = suggestions
        super().__init__(message)


class SmarterMCPServerToolError(SmarterMCPServerException):
    """
    A tool could not do what it was asked, e.g. a file does not exist.

    The error is returned to the LLM as the tool's result, with ``isError`` set, so that it
    can correct its arguments. Because a tool raises it, rather than returning the message, a
    failed tool call is never cached (see :mod:`smarter.apps.mcpserver.protocol.caching`).
    """

    @property
    def get_formatted_err_message(self) -> str:
        """
        Return the title of the error, as the platform's error responses show it.

        :returns: ``"Smarter MCPServer tool error"``.
        """
        return "Smarter MCPServer tool error"
