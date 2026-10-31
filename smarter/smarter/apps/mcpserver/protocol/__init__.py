"""
The Smarter Project MCP server's protocol layer: what MCP clients see and call.

- :mod:`~smarter.apps.mcpserver.protocol.views`: the Streamable HTTP endpoint, a Django view.
- :mod:`~smarter.apps.mcpserver.protocol.server`: answers the JSON-RPC messages of one request.
- :mod:`~smarter.apps.mcpserver.protocol.tools`: the tools' base class, and the scope that they work on.
- :mod:`~smarter.apps.mcpserver.protocol.registry`: every tool, from the feature packages
  :mod:`~smarter.apps.mcpserver.index`, :mod:`~smarter.apps.mcpserver.manifests` and
  :mod:`~smarter.apps.mcpserver.github`.
"""
