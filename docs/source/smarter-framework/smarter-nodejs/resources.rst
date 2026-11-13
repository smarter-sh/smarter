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
       ``stream()``, ``config()``, ``providerRequest()``, their ``plugins()``, ``functions()``, ``apiKeys()`` and
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
       reads a plugin's manifest by its id. ``vectorsearches.run()`` runs a
       :doc:`Vectorsearch <../../smarter-resources/smarter-vectorsearch>`.
   * - ``client.extensions``
     - The platform's :doc:`extensions <../../smarter-platform/extensions>` and the extension
       registry: ``list()``, ``registry()``, ``retrieve()``, and for superusers ``checkUpdates()``,
       ``install()``, ``upload()``, ``configure()``, ``enable()``, ``disable()``, ``update()``,
       ``rollback()``, ``setAvailability()`` and ``uninstall()``.
   * - ``client.accounts``
     - Accounts, and ``accounts.users``, ``accounts.userProfiles`` (each user's membership of an
       account) and ``accounts.contacts``, for superusers. Every user reads their own token usage,
       ``accounts.usage()``, and exports their own data, ``accounts.dataExports``.
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

Vectorsearches
--------------

A Vectorsearch is a saved retrieval pipeline over a vectorstore: its search type, ``k``, score
threshold and metadata filter. ``run()`` searches with them, and an optional ``filter`` narrows the
results further; the Vectorsearch's own ``metadataFilter`` wins where both name the same key.

.. code-block:: typescript

   const found = await client.vectorsearches.run("rMTAwMDAxMgx", "How long is the refund window?", {
     filter: { topic: "refunds" },
   });
   for (const hit of found.results) console.log(hit.score, hit.text, hit.metadata);

The platform answers 400 (``BadRequestError``) when the Vectorsearch is disabled, and 402
(``PaymentRequiredError``) when a :doc:`budget <../../smarter-resources/smarter-budget>` forbids the
search.

Extensions
----------

:doc:`Extensions <../../smarter-platform/extensions>` add tools to the LLMClients that use them.
Every user reads the extensions that their account may use; a superuser also sees their settings, and
manages them. An extension is installed disabled: configure its settings, then enable it.

.. code-block:: typescript

   const installed = await client.extensions.list();
   for (const extension of installed.objects) console.log(extension.slug, extension.installedVersion, extension.enabled);
   for (const item of (await client.extensions.registry()).objects) console.log(item.slug, item.action);

   // superusers only
   await client.extensions.install("weather");
   await client.extensions.configure("weather", {
     values: { weather_api_url: null }, // null resets a setting to its default
     secrets: { google_maps_api_key: { secretId: 6 } }, // one of the platform admin's Secrets, or { value: "..." }
   });
   const result = await client.extensions.enable("weather");
   console.log(result.message, result.extension?.tools.map((tool) => tool.functionName));

``upload()`` installs an extension from its .zip archive (a path, a ``file:`` url, or a ``File``),
``setAvailability(slug, false, { accountIds })`` limits it to some accounts, and ``rollback(slug,
versionId)`` runs one of its earlier installed versions. A user who is not a superuser gets a
``PermissionDeniedError`` from every action.

Token usage and data exports
----------------------------

Every user may read the tokens and cost of their own LLM requests, the series that the web console's
dashboard charts (see :doc:`Cost Accounting <../../smarter-platform/cost-accounting>`), one point per
hour, day or month. Its points are snake_case, as the platform sends them.

.. code-block:: typescript

   const usage = await client.accounts.usage({ periodicity: "7_days" }); // 12_hours, 24_hours (the default), 7_days, 1_month or 1_year
   for (const point of usage.points) console.log(point.period_start, point.total_tokens, point.total_cost);

A data export is a zip file of the manifest of every resource that the user owns, with Secrets'
values redacted. The platform builds it in the background, and emails the user a link to it: the API
never returns the link or the file.

.. code-block:: typescript

   const overview = await client.accounts.dataExports.overview();
   console.log(overview.email, overview.exportsLeftToday, overview.latest?.status);
   const started = await client.accounts.dataExports.start();
   console.log((await client.accounts.dataExports.retrieve(started.id)).step);

``start()`` returns the export that is already in progress, if there is one. It throws a
``RateLimitError`` (429) when the user has no email address or has started too many exports today,
and the SDK doesn't retry that refusal.

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
