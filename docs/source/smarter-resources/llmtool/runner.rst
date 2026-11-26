Tool Runner
===========

Every LLM tool call is resolved in the app into a serializable call, with the credentials it needs,
and executed by the tool runner. Today the runner executes it in the app's own process. The
boundary is where :doc:`ADR-038 </adr/038-tool-isolation-and-egress>` moves tool calls into a
worker that holds no credentials. MCP clients go through it.

.. automodule:: smarter.apps.llmtool.runner.models
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: smarter.apps.llmtool.runner.runner
    :members:
    :undoc-members:
    :show-inheritance:
