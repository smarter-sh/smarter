Tool Runner
===========

.. image:: ../../_static/tool-runner.svg
   :alt: When the LLM asks for a tool, the tool's code in the app checks the permissions and the cache. On a cache
         miss it resolves the call, decrypting the credential from its Smarter Secret, into a ToolCall of plain values.
         The tool runner, from get_tool_runner(), finds the executor of the call's kind in TOOL_EXECUTORS:
         execute_mcp_call for MCP clients, execute_api_call for API plugins. The executor reads no database and no
         Secret, and calls the MCP server or the api. Its ToolCallResult returns to the tool's code in the app, which
         sends the signals, caches the result and gives it to the LLM. Today execution runs in the app's process; in
         phase 2 of ADR-038 it moves to a worker without credentials.
   :width: 100%

Every LLM tool call is resolved in the app into a serializable call, with the credentials it needs,
and executed by the tool runner. Today the runner executes it in the app's own process. The
boundary is where :doc:`ADR-038 </adr/038-tool-isolation-and-egress>` moves tool calls into a
worker that holds no credentials.

The tool's own code stays in the app, around the runner: it checks the permissions and the cache,
resolves the call only when the cache misses, so that a credential is read only for a call that
runs, and, from the result, sends the signals, stores the result in the cache and answers the LLM.
The executor of each kind of call, registered in ``TOOL_EXECUTORS``, reads no database and no
Smarter Secret. Today MCP clients (:mod:`smarter.apps.mcpclient.execution`) and API plugins
(:mod:`smarter.apps.connection.execution`) go through it.

.. automodule:: smarter.apps.llmtool.runner.models
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: smarter.apps.llmtool.runner.runner
    :members:
    :undoc-members:
    :show-inheritance:
