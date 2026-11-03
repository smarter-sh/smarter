"""
The MCPServer's tools: thin adapters of its services, for an LLM.

Each tool has a name, a description written for the LLM, and a Pydantic model of its arguments,
from which its JSON Schema is generated. Its ``run`` validates the call, calls a service of
:mod:`smarter.apps.mcpserver.services`, and formats what it returns as Markdown.

- :mod:`~smarter.apps.mcpserver.protocol.tools.public`: the base class of the public tools, which
  caches their results, and the repositories that they work on.
- :mod:`~smarter.apps.mcpserver.protocol.tools.staff`: the base class of the staff-only tools,
  which records every call in the audit trail.
- The public tools: :mod:`~smarter.apps.mcpserver.protocol.tools.search`,
  :mod:`~smarter.apps.mcpserver.protocol.tools.reading`,
  :mod:`~smarter.apps.mcpserver.protocol.tools.manifests` and
  :mod:`~smarter.apps.mcpserver.protocol.tools.github`.
- The staff-only tools: :mod:`~smarter.apps.mcpserver.protocol.tools.status`,
  :mod:`~smarter.apps.mcpserver.protocol.tools.logs` and
  :mod:`~smarter.apps.mcpserver.protocol.tools.helpdesk`.
- :mod:`~smarter.apps.mcpserver.protocol.tools.markdown`: the Markdown helpers that they share.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""
