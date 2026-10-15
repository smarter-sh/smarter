Resources
=========

Each resource family is a property of the client. Every family that has a REST API can ``list()``
its resources, ``retrieve()`` one by its id or hashed id, and ``find()`` one by name, and every
family has the manifest operations described in :doc:`Manifests <manifests>`. Beyond those, each
family has the actions that its REST API offers. Every method returns a promise, and takes a last
options object with its own optional arguments, and ``signal``, ``timeout`` and ``headers``.

What a user can see and do is decided by the platform: the API key's user reads the resources of
their account, and only a resource's owner may change it. Some endpoints, e.g. the Smarter Journal,
are for superusers only.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Property
     - Resources and actions
   * - ``client.manifests``
     - Any kind, through the manifest API. See :doc:`Manifests <manifests>`.
   * - ``client.llmClients``
     - :doc:`LLMClients <../../smarter-resources/smarter-llmclient>`: ``prompt()``, ``chat()``,
       ``stream()``, ``config()``, their ``plugins()``, ``functions()``, ``apiKeys()`` and
       ``customDomains()``, and ``deploy()``. An LLMClient's ``tools`` list everything that it adds
       to a prompt: its functions, plugins, MCPClients (``mcpclients``) and guardrails
       (``guardrails``). See :doc:`Prompts and Chat <chat>`.
   * - ``client.guardrails``
     - :doc:`Guardrails <../../smarter-resources/smarter-guardrail>`: ``evaluate()`` and ``events()``.
   * - ``client.mcpClients``
     - :doc:`MCPClients <../../smarter-resources/smarter-mcpclient>`: ``tools()``, ``refresh()`` and
       ``callTool()``.
   * - ``client.vectorstores``
     - :doc:`Vectorstores <../../smarter-resources/smarter-vectorstore>`: ``status()``, ``deploy()``,
       ``documents()``, ``addText()``, ``addUrl()``, ``addFiles()``, ``deleteDocument()``,
       ``search()``, ``snapshots()``, ``createSnapshot()`` and ``restore()``.
   * - ``client.llmHosts``
     - LLMHosts: ``status()``, ``logs()``, ``plan()``, ``deploy()``, ``undeploy()``, ``report()``,
       ``discover()`` and ``discoverManifest()``.
   * - ``client.secrets``, ``client.plugins``, ``client.orchestrators``, ``client.vectorsearches``
     - Read them, and manage them with manifests. A plugin's manifest kind is its class, e.g.
       ``SqlPlugin``, which ``client.plugins`` looks up for you. ``plugins.retrieveManifest(id)``
       reads a plugin's manifest by its id.
   * - ``client.accounts``
     - Accounts, and ``accounts.users``, ``accounts.userProfiles`` (each user's membership of an
       account) and ``accounts.contacts``. Superusers only.
   * - ``client.history``
     - The chat sessions, their tool calls and their plugin uses, newest first: the user's own, their
       account's users' for an account admin, and every one for a superuser.
   * - ``client.journal``
     - The :doc:`Smarter Journal <../smarter-api/smarter-journal>`, page by page. Superusers only.
   * - ``client.providers``
     - The LLM providers that the platform is configured for, and their models.
   * - ``client.proxies``
     - Proxies to LLM providers' own APIs: ``baseUrl()`` and ``request()``.
   * - ``client.whoami()``, ``version()``, ``status()``, ``kinds()``
     - The API key's user and account, the platform's version and state, and its resource kinds.

Guardrails
----------

Dry-run a Guardrail on a text, e.g. to test a new pattern before you rely on it. Nothing is saved.

.. code-block:: typescript

   const result = await client.guardrails.evaluate(guardrail.id, "My card is 4111 1111 1111 1111");
   if (result.triggered) console.log(result.disposition, result.text); // e.g. redacted "My card is [REDACTED]"
   for (const event of (await client.guardrails.events(guardrail.id, { reviewed: false })).events) {
     console.log(event.createdAt, event.llmclient, event.disposition);
   }

MCP clients
-----------

.. code-block:: typescript

   const tools = await client.mcpClients.tools(mcpclient.id);
   for (const tool of tools.tools) console.log(tool.name, tool.inputSchema);
   const result = await client.mcpClients.callTool(mcpclient.id, "aws___search_documentation", { search_phrase: "S3" });
   console.log(result.isError, result.content);

Only an MCPClient's owner may call its tools.

Vectorstores
------------

.. code-block:: typescript

   await client.vectorstores.addText(store.id, "Our refund window is 30 days.", { name: "refunds" });
   await client.vectorstores.addUrl(store.id, "https://example.com/faq");
   await client.vectorstores.addFiles(store.id, ["handbook.pdf", "policies.docx"]);
   const found = await client.vectorstores.search(store.id, "How long is the refund window?", { k: 3 });
   for (const hit of found.results) console.log(hit.score, hit.text);

``addFiles()`` takes paths, ``file:`` urls, or ``File`` objects. Documents are split, embedded and
loaded asynchronously, and only once the vectorstore is deployed. The platform serves these
endpoints when ``SMARTER_ENABLE_VECTORSTORE`` is true.

LLMHosts
--------

An LLMHost serves an open-weight model on the platform's own cluster. ``plan()`` shows the
Kubernetes resources that ``deploy()`` would create, without creating them. Deploying creates real,
billable infrastructure, which may include GPU nodes.

.. code-block:: typescript

   for (const model of await client.llmHosts.discover({ query: "qwen", task: "chat", limit: 5 })) {
     console.log(model.repository, model.downloads);
   }
   const manifest = await client.llmHosts.discoverManifest("Qwen/Qwen2.5-7B-Instruct");
   await client.llmHosts.apply(manifest);
   console.log((await client.llmHosts.report()).totals);

Proxies
-------

A Proxy gives authenticated, governed access to an LLM provider's own API: the platform holds the
provider's key, and you use your Smarter API key instead. The easiest client of a proxy is the
provider's own SDK:

.. code-block:: typescript

   import OpenAI from "openai";
   import { Smarter } from "@smarter.sh/api";

   const smarter = new Smarter();
   const openai = new OpenAI({ baseURL: smarter.proxies.baseUrl("openai"), apiKey: smarter.apiKey });

The platform serves proxies when ``SMARTER_ENABLE_PROXY`` is true.

Endpoints the SDK does not wrap
-------------------------------

``client.http`` is the SDK's authenticated transport. Use it for an endpoint that the SDK doesn't
wrap yet, with the same retries and errors, and a Zod schema of the response:

.. code-block:: typescript

   import { JsonValue } from "@smarter.sh/api";

   const data = await client.http.request("GET", "llmhosts/report/", JsonValue);
