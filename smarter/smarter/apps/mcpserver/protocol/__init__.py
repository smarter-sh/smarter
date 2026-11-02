"""
The MCP servers' protocol layer: what MCP clients see and call.

- :mod:`~smarter.apps.mcpserver.protocol.base`: the Model Context Protocol over Streamable HTTP,
  shared by every server: the JSON-RPC handling, and the base classes of a server and a tool.
- :mod:`~smarter.apps.mcpserver.protocol.views`: the Streamable HTTP endpoints, Django views.

The Smarter Project MCP server, public, of The Smarter Project's repositories, documentation and blog:

- :mod:`~smarter.apps.mcpserver.protocol.server`: the server.
- :mod:`~smarter.apps.mcpserver.protocol.tools`: the tools' base class, and the scope that they work on.
- :mod:`~smarter.apps.mcpserver.protocol.registry`: every tool, from the feature packages
  :mod:`~smarter.apps.mcpserver.index`, :mod:`~smarter.apps.mcpserver.manifests` and
  :mod:`~smarter.apps.mcpserver.github`.

The Smarter Operations MCP server, for the platform's staff only, of its health, logs and users:

- :mod:`~smarter.apps.mcpserver.protocol.operations_server`: the server, and its tools.
- :mod:`~smarter.apps.mcpserver.protocol.operations_tools`: the tools' base class, which records
  every call in the audit trail.
"""
