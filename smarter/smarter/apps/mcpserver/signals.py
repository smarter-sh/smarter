"""
Django signals of the MCPServer app.

The MCPServer sends them when a client calls one, and when one of their tools is called. The
indexers send them after each attempt to index a repository or the blog. Their receivers, in
:mod:`smarter.apps.mcpserver.receivers`, log each event, and make the cached tool results
stale when an index changes. Other apps may connect their own receivers.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.dispatch import Signal

mcpserver_called = Signal()
"""
Signal sent when a client sends a JSON-RPC request, or a notification, to the MCPServer.

Sent by :mod:`smarter.apps.mcpserver.protocol.base`, before the request is handled. Received by
:func:`~smarter.apps.mcpserver.receivers.handle_mcpserver_called`, which logs it.

Arguments:
    server (str): The server's name, e.g. smarter-project-smarter-cli.
    method (str): The JSON-RPC method, e.g. tools/call.

Example::

    mcpserver_called.send(sender=self.__class__, server=self.name, method="tools/list")
"""

mcpserver_tool_called = Signal()
"""
Signal sent when one of the MCPServer's tools has been called.

Sent by :mod:`smarter.apps.mcpserver.protocol.base`, after the tool has returned a result, or
raised :class:`~smarter.apps.mcpserver.exceptions.SmarterMCPServerToolError`. Received by
:func:`~smarter.apps.mcpserver.receivers.handle_mcpserver_tool_called`, which logs it.

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
Signal sent when a repository, or the blog, has been indexed at a new commit.

Sent by :func:`smarter.apps.mcpserver.services.indexing.github.index_repository` and
:func:`smarter.apps.mcpserver.services.indexing.blog.index_blog`. It is not sent when the index was already
up to date. Received by
:func:`~smarter.apps.mcpserver.receivers.handle_mcpserver_repository_indexed`, which makes the
cached tool results stale, and logs it.

Arguments:
    index (RepositoryIndex): The repository's index.

Example::

    mcpserver_repository_indexed.send(sender=index_repository, index=index)
"""

mcpserver_repository_index_failed = Signal()
"""
Signal sent when a repository, or the blog, could not be indexed.

Sent by :func:`smarter.apps.mcpserver.services.indexing.github.index_repository` and
:func:`smarter.apps.mcpserver.services.indexing.blog.index_blog`, after the error is recorded in the
index's ``error``. Received by
:func:`~smarter.apps.mcpserver.receivers.handle_mcpserver_repository_index_failed`, which logs
it at WARNING.

Arguments:
    repository (str): The repository's name.
    error (str): Why.

Example::

    mcpserver_repository_index_failed.send(sender=index_repository, repository="smarter-cli", error="...")
"""
