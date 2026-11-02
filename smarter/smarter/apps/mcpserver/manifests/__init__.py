"""
The platform's manifests, and the Smarter Project MCP server's tools that read and validate them.

An LLM that writes a Smarter manifest needs to know which fields its kind has, and whether
what it wrote is valid. This package answers both from the platform's own committed JSON
Schemas and its own validation, so the answers match the platform's version.

- :mod:`~smarter.apps.mcpserver.manifests.schemas`: the kinds' JSON Schemas and examples, and validation.
- :mod:`~smarter.apps.mcpserver.manifests.tools`: ``get_manifest_schema`` and ``validate_manifest``.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""
