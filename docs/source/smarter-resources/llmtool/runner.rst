Tool Runner
===========

.. image:: ../../_static/tool-runner.svg
   :alt: When the LLM asks for a tool, the tool's code in the app checks the permissions and the cache. On a cache
         miss it resolves the call, decrypting the credential from its Smarter Secret, into a ToolCall of plain values.
         The tool runner, from get_tool_runner(), finds the executor of the call's kind in TOOL_EXECUTORS:
         execute_mcp_call for MCP clients, execute_api_call for API plugins, execute_sql_call for SQL plugins,
         through an SSH tunnel when the connection uses one, execute_http_call for the web search
         apis, the Brave image search, the checks of each image's url and websites' robots.txt, and
         execute_webfetch_call for the pages that the web search plugin reads, with its domain policy and robots.txt
         checked again on each redirect. The executor reads neither the app's database nor a Secret, and calls the MCP
         server, the api, the SqlConnection's database, the search api or the website. Its ToolCallResult returns to the tool's code in the app, which
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
Smarter Secret. Today these go through it:

- MCP clients, with :mod:`smarter.apps.mcpclient.execution`;
- API plugins, with :mod:`smarter.apps.connection.execution`;
- SQL plugins, with :mod:`smarter.apps.connection.execution`, through an SSH tunnel
  (:mod:`smarter.apps.connection.ssh`) for a connection that uses one;
- the WebsearchPlugin's search apis (Brave, Tavily), the ImageSearchPlugin's Brave image search and
  its checks of each image's url, and every website's robots.txt, with
  :mod:`smarter.apps.llmtool.runner.http`. Its ``fetch_with_runner()`` takes the place of
  ``safe_http.fetch()``, so each of them changed by one line;
- the WebsearchPlugin's fetch of a page, with ``WebFetchToolCall`` and ``execute_webfetch_call()`` in
  :mod:`smarter.apps.llmtool.plugin.websearch_fetch`. ``fetch``'s ``redirect_policy`` is a function,
  which can't travel with a call, so the call carries what it decides on, the domain policy and
  whether to obey robots.txt, and the executor builds the function where the call runs.

.. automodule:: smarter.apps.llmtool.runner.http
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: smarter.apps.llmtool.runner.models
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: smarter.apps.llmtool.runner.runner
    :members:
    :undoc-members:
    :show-inheritance:
