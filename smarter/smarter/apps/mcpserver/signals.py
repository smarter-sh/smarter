"""
Signals for the mcpserver app.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.dispatch import Signal

mcpserver_called = Signal()
"""
Signal sent when a client sends a JSON-RPC request to the Smarter Project MCP server.

Arguments:
    server (str): The server's name, e.g. smarter-project-smarter-cli.
    method (str): The JSON-RPC method, e.g. tools/call.

Example::

    mcpserver_called.send(sender=self.__class__, server=self.name, method="tools/list")
"""

mcpserver_tool_called = Signal()
"""
Signal sent when one of the MCP server's tools has been called.

Arguments:
    server (str): The server's name.
    tool_name (str): The tool.
    arguments (dict): The tool's arguments.
    is_error (bool): Whether the tool returned an error.
    characters (int): The length of the result.

Example::

    mcpserver_tool_called.send(sender=self.__class__, server=self.name, tool_name="read_file", arguments={}, is_error=False, characters=1200)
"""

mcpserver_repository_indexed = Signal()
"""
Signal sent when a repository has been indexed at a new commit.

Arguments:
    index (RepositoryIndex): The repository's index.

Example::

    mcpserver_repository_indexed.send(sender=index_repository, index=index)
"""

mcpserver_repository_index_failed = Signal()
"""
Signal sent when a repository could not be indexed.

Arguments:
    repository (str): The repository's name.
    error (str): Why.

Example::

    mcpserver_repository_index_failed.send(sender=index_repository, repository="smarter-cli", error="...")
"""
