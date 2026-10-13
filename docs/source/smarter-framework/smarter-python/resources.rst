Resources
=========

Each resource family is an attribute of the client. Every family that has a REST API can
``list()`` its resources, ``retrieve()`` one by its id or hashed id, and ``find()`` one by name, and
every family has the manifest operations described in :doc:`Manifests <manifests>`. Beyond those,
each family has the actions that its REST API offers.

What a user can see and do is decided by the platform: the API key's user reads the resources of
their account, and only a resource's owner may change it. Some endpoints, e.g. the Smarter Journal,
are for superusers only.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Attribute
     - Resources and actions
   * - ``client.manifests``
     - Any kind, through the manifest API. See :doc:`Manifests <manifests>`.
   * - ``client.llm_clients``
     - :doc:`LLMClients <../../smarter-resources/smarter-llmclient>`: ``prompt()``, ``chat()``,
       ``stream()``, ``config()``, their plugins, functions, api keys and custom domains, and
       ``deploy()``. See :doc:`Prompts and Chat <chat>`.
   * - ``client.guardrails``
     - :doc:`Guardrails <../../smarter-resources/smarter-guardrail>`: ``evaluate()`` and ``events()``.
   * - ``client.mcp_clients``
     - :doc:`MCPClients <../../smarter-resources/smarter-mcpclient>`: ``tools()``, ``refresh()`` and
       ``call_tool()``.
   * - ``client.vectorstores``
     - :doc:`Vectorstores <../../smarter-resources/smarter-vectorstore>`: ``status()``, ``deploy()``,
       ``documents()``, ``add_text()``, ``add_url()``, ``add_files()``, ``delete_document()``,
       ``search()``, ``snapshots()``, ``create_snapshot()`` and ``restore()``.
   * - ``client.llm_hosts``
     - LLMHosts: ``status()``, ``logs()``, ``plan()``, ``deploy()``, ``undeploy()``, ``report()``,
       ``discover()`` and ``discover_manifest()``.
   * - ``client.secrets``, ``client.plugins``, ``client.orchestrators``, ``client.vectorsearches``
     - Read them, and manage them with manifests. A plugin's manifest kind is its class, e.g.
       ``SqlPlugin``, which ``client.plugins`` looks up for you.
   * - ``client.accounts``
     - Accounts, and ``accounts.users``, ``accounts.user_profiles`` (each user's membership of an
       account) and ``accounts.contacts``. Superusers only.
   * - ``client.history``
     - The chat sessions, their tool calls and their plugin uses, newest first: the user's own, their
       account's users' for an account admin, and every one for a superuser.
   * - ``client.journal``
     - The :doc:`Smarter Journal <../smarter-api/smarter-journal>`, page by page. Superusers only.
   * - ``client.providers``
     - The LLM providers that the platform is configured for, and their models.
   * - ``client.proxies``
     - Proxies to LLM providers' own APIs: ``base_url()`` and ``request()``.
   * - ``client.whoami()``, ``version()``, ``status()``, ``kinds()``
     - The API key's user and account, the platform's version and state, and its resource kinds.

Guardrails
----------

Dry-run a Guardrail on a text, e.g. to test a new pattern before you rely on it. Nothing is saved.

.. code-block:: python

   result = client.guardrails.evaluate(guardrail.id, "My card is 4111 1111 1111 1111")
   if result.triggered:
       print(result.disposition, result.text)          # e.g. redacted "My card is [REDACTED]"
   for event in client.guardrails.events(guardrail.id, reviewed=False).events:
       print(event.created_at, event.llmclient, event.disposition)

MCP clients
-----------

.. code-block:: python

   tools = client.mcp_clients.tools(mcpclient.id)
   for tool in tools.tools:
       print(tool.name, tool.input_schema)
   result = client.mcp_clients.call_tool(mcpclient.id, "aws___search_documentation", {"search_phrase": "S3"})
   print(result.is_error, result.content)

Only an MCPClient's owner may call its tools.

Vectorstores
------------

.. code-block:: python

   client.vectorstores.add_text(store.id, "Our refund window is 30 days.", name="refunds")
   client.vectorstores.add_url(store.id, "https://example.com/faq")
   client.vectorstores.add_files(store.id, ["handbook.pdf", "policies.docx"])
   for hit in client.vectorstores.search(store.id, "How long is the refund window?", k=3).results:
       print(hit.score, hit.text)

Documents are split, embedded and loaded asynchronously, and only once the vectorstore is deployed.
The platform serves these endpoints when ``SMARTER_ENABLE_VECTORSTORE`` is true.

LLMHosts
--------

An LLMHost serves an open-weight model on the platform's own cluster. ``plan()`` shows the
Kubernetes resources that ``deploy()`` would create, without creating them. Deploying creates real,
billable infrastructure, which may include GPU nodes.

.. code-block:: python

   for model in client.llm_hosts.discover(query="qwen", task="chat", limit=5):
       print(model.repository, model.downloads)
   manifest = client.llm_hosts.discover_manifest("Qwen/Qwen2.5-7B-Instruct")
   client.llm_hosts.apply(manifest)
   print(client.llm_hosts.report().totals)

Proxies
-------

A Proxy gives authenticated, governed access to an LLM provider's own API: the platform holds the
provider's key, and you use your Smarter API key instead. The easiest client of a proxy is the
provider's own SDK:

.. code-block:: python

   from openai import OpenAI
   from smarter import Smarter

   smarter = Smarter()
   openai = OpenAI(base_url=smarter.proxies.base_url("openai"), api_key=smarter.api_key)

The platform serves proxies when ``SMARTER_ENABLE_PROXY`` is true.

Endpoints the SDK does not wrap
-------------------------------

``client.http`` is the SDK's authenticated transport. Use it for an endpoint that the SDK doesn't
wrap yet, with the same retries and errors:

.. code-block:: python

   from smarter.core.typing import SmarterJsonType

   data = client.http.request("GET", "llmhosts/report/", cast_to=SmarterJsonType)
