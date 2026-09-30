"""
Signals for the mcpclient app.

These signals report the lifecycle of connections to MCP servers, and of the tool
calls and resource reads that LLMs make through them.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.dispatch import Signal

mcpclient_called = Signal()
"""
Signal sent when an MCPClient api endpoint is called.

Arguments:
    mcpclient (MCPClient): The mcpclient instance.
    request (HttpRequest): The HTTP request object.
    args: Positional arguments.
    kwargs: Keyword arguments.

Example::

    mcpclient_called.send(sender=self.__class__, mcpclient=self.mcpclient, request=request, args=args, kwargs=kwargs)
"""

mcpclient_connected = Signal()
"""
Signal sent when Smarter connects to an MCP server and fetches its catalog.

Arguments:
    mcpclient (MCPClient): The MCPClient.
    catalog (MCPServerCatalog): What the server reported.

Example::

    mcpclient_connected.send(sender=self.__class__, mcpclient=mcpclient, catalog=catalog)
"""

mcpclient_connection_failed = Signal()
"""
Signal sent when Smarter cannot connect to an MCP server, or fetch its catalog.

Arguments:
    mcpclient (MCPClient): The MCPClient.
    error (str): A description of the error.

Example::

    mcpclient_connection_failed.send(sender=self.__class__, mcpclient=mcpclient, error=str(e))
"""

mcpclient_tool_called = Signal()
"""
Signal sent when an LLM calls an MCP server's tool, before the call.

Arguments:
    mcpclient (MCPClient): The MCPClient.
    tool_name (str): The name of the tool, as the server reports it.
    arguments (dict): The tool's arguments.

Example::

    mcpclient_tool_called.send(sender=self.__class__, mcpclient=mcpclient, tool_name=name, arguments=arguments)
"""

mcpclient_tool_responded = Signal()
"""
Signal sent when an MCP server's tool returns a result.

Arguments:
    mcpclient (MCPClient): The MCPClient.
    tool_name (str): The name of the tool.
    is_error (bool): True if the tool reported an error.
    characters (int): The length of the result returned to the LLM.

Example::

    mcpclient_tool_responded.send(
        sender=self.__class__, mcpclient=mcpclient, tool_name=name, is_error=False, characters=1234
    )
"""

mcpclient_tool_failed = Signal()
"""
Signal sent when an MCP server's tool cannot be called, e.g. because the server is unreachable.

Arguments:
    mcpclient (MCPClient): The MCPClient.
    tool_name (str): The name of the tool.
    error (str): A description of the error, which is also returned to the LLM.

Example::

    mcpclient_tool_failed.send(sender=self.__class__, mcpclient=mcpclient, tool_name=name, error=str(e))
"""

mcpclient_resource_read = Signal()
"""
Signal sent when an LLM reads an MCP server's resource.

Arguments:
    mcpclient (MCPClient): The MCPClient.
    uri (str): The URI of the resource.
    characters (int): The length of the content returned to the LLM.

Example::

    mcpclient_resource_read.send(sender=self.__class__, mcpclient=mcpclient, uri=uri, characters=1234)
"""
