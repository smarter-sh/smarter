"""
The MCPServer's protocol layer: the Model Context Protocol, and the tools that MCP clients call.

The MCPServer serves its tools at two endpoints, each a set of tools over the same protocol code:

- ``/api/v1/mcp/smarter-project/``: the public tools, of The Smarter Project's repositories,
  documentation, blog, manifests and GitHub issues
  (:mod:`~smarter.apps.mcpserver.protocol.public`). Smarter's built-in ``smarter_project`` MCPClient
  connects to it.
- ``/api/v1/mcp/smarter-operations/``: the staff-only tools, of this platform's health, logs and
  users (:mod:`~smarter.apps.mcpserver.protocol.staff`). The built-in ``smarter_operations``
  MCPClient connects to it.

The modules:

- :mod:`~smarter.apps.mcpserver.protocol.base`: the Model Context Protocol over Streamable HTTP:
  the JSON-RPC handling, and the base classes of an endpoint and a tool.
- :mod:`~smarter.apps.mcpserver.protocol.public` and :mod:`~smarter.apps.mcpserver.protocol.staff`:
  the two endpoints, with their instructions for the LLM.
- :mod:`~smarter.apps.mcpserver.protocol.toolsets`: the tools of each endpoint.
- :mod:`~smarter.apps.mcpserver.protocol.tools`: the tools, thin adapters of the services of
  :mod:`smarter.apps.mcpserver.services`.
- :mod:`~smarter.apps.mcpserver.protocol.views`: the Django views of the endpoints.
- :mod:`~smarter.apps.mcpserver.protocol.auth`: who is calling: the caller's GitHub token, and the
  platform's staff.
- :mod:`~smarter.apps.mcpserver.protocol.ratelimit`: the rate limit of each client IP address.
- :mod:`~smarter.apps.mcpserver.protocol.caching`: the cache of the public tools' results.

The protocol layer imports the services, and the services never import it.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""
