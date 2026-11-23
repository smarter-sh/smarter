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
     - :doc:`LLMClients </smarter-resources/smarter-llmclient>`: ``prompt()``, ``chat()``,
       ``stream()``, ``config()``, their plugins, functions, api keys and custom domains, and
       ``deploy()``. An LLMClient's ``tools`` list everything that it adds to a prompt: its
       functions, plugins, MCPClients (``mcpclients``) and guardrails (``guardrails``). See
       :doc:`Prompts and Chat <chat>`.
   * - ``client.guardrails``
     - :doc:`Guardrails </smarter-resources/smarter-guardrail>`: ``evaluate()`` and ``events()``.
   * - ``client.mcp_clients``
     - :doc:`MCPClients </smarter-resources/smarter-mcpclient>`: ``tools()``, ``refresh()`` and
       ``call_tool()``.
   * - ``client.vectorstores``
     - :doc:`Vectorstores </smarter-resources/smarter-vectorstore>`: ``status()``, ``deploy()``,
       ``documents()``, ``add_text()``, ``add_url()``, ``add_files()``, ``delete_document()``,
       ``search()``, ``snapshots()``, ``create_snapshot()`` and ``restore()``.
   * - ``client.llm_hosts``
     - LLMHosts: ``status()``, ``logs()``, ``plan()``, ``deploy()``, ``undeploy()``, ``report()``,
       ``discover()`` and ``discover_manifest()``.
   * - ``client.vectorsearches``
     - Vectorsearches, saved searches of a vectorstore: ``run()``.
   * - ``client.orchestrators``
     - Orchestrators, multi-agent workflows over LLMClients: ``run()`` starts a run toward an
       objective, which the platform executes in the background, ``run_status()`` reads it until
       its ``done``, and ``runs()`` lists the newest.
   * - ``client.secrets``, ``client.plugins``
     - Read them, and manage them with manifests. A plugin's manifest kind is its class, e.g.
       ``SqlPlugin``, which ``client.plugins`` looks up for you.
   * - ``client.extensions``
     - The platform's extensions, packages of LLM tools: ``list()``, ``registry()``, ``retrieve()``,
       and, for superusers, ``install()``, ``upload()``, ``configure()``, ``enable()``, ``disable()``,
       ``update()``, ``rollback()``, ``set_availability()``, ``check_updates()`` and ``uninstall()``.
   * - ``client.accounts``
     - Accounts, and ``accounts.users``, ``accounts.user_profiles`` (each user's membership of an
       account) and ``accounts.contacts``: superusers only. Every user may read their own token
       usage with ``accounts.usage()``, and export their own data with ``accounts.data_exports``.
   * - ``client.history``
     - The chat sessions, their tool calls and their plugin uses, newest first: the user's own, their
       account's users' for an account admin, and every one for a superuser.
   * - ``client.journal``
     - The :doc:`Smarter Journal </smarter-framework/smarter-api/smarter-journal>`, page by page. Superusers only.
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
The platform serves these endpoints when ``SMARTER_APP_VECTORSTORE_ENABLE`` is true.

Vectorsearches
--------------

A Vectorsearch is a saved search of one vectorstore: its search type, ``k``, score threshold and
metadata filter. ``run()`` searches with that configuration. A ``filter`` adds metadata that every
result must match; the Vectorsearch's own filter wins where both name the same key, so a filter can
narrow a Vectorsearch, but never widen it.

.. code-block:: python

   results = client.vectorsearches.run(vectorsearch.id, "How long is the refund window?", filter={"lang": "en"})
   for hit in results.results:
       print(hit.score, hit.text)

The platform answers 400 (``BadRequestError``) when the Vectorsearch is disabled, and 402
(``PaymentRequiredError``) when a budget locks the Vectorsearch, the user's profile or their account.

Extensions
----------

An extension is a package of LLM tools that a superuser installs on the platform, from the
:doc:`Smarter extension registry </smarter-platform/system-administration/llm-providers-and-extensions/extensions>` or from a
.zip archive, and that LLMClients then offer the LLM. Every user may list the extensions that their
account may use; only superusers may install and manage them, and other users get a
``PermissionDeniedError``. An extension is installed disabled: configure its settings, then enable it.

.. code-block:: python

   for entry in client.extensions.registry().objects:
       print(entry.slug, entry.latest_version, entry.action)    # e.g. weather 0.2.1 install

   client.extensions.install("weather")
   client.extensions.configure(
       "weather",
       values={"weather_api_url": None},                        # None resets a setting to its default
       secrets={"google_maps_api_key": "AIza..."},              # saved encrypted in a new Secret
   )
   client.extensions.enable("weather")
   client.extensions.set_availability("weather", all_accounts=False, account_ids=[2, 5])

   weather = client.extensions.retrieve("weather")
   print(weather.installed_version, [tool.function_name for tool in weather.tools])

A secret setting's value is a string to save in a new Secret, the id of one of the platform admin's
Secrets, or ``None`` to clear it. ``upload()`` installs an archive by its path, or from a binary file
object. ``rollback()`` takes the id of one of the extension's ``versions``. The extensions of one
LLMClient are ``client.llm_clients.extensions()``.

Token usage and data exports
----------------------------

Every user may read the tokens and cost of their own LLM requests, one point per hour, day or
month, oldest first. The window is ``12_hours``, ``24_hours`` (the default), ``7_days``,
``1_month`` or ``1_year``.

.. code-block:: python

   for point in client.accounts.usage("7_days").points:
       print(point.period_start.date(), point.total_tokens, point.total_cost)

``accounts.data_exports`` is the web console's Download My Data: a zip file of the manifest of
every resource that the user owns, with Secrets' values redacted. The platform builds it in the
background and emails the user a link to it; the API never returns the link.

.. code-block:: python

   overview = client.accounts.data_exports.overview()
   print(overview.email, overview.exports_left_today)
   export = client.accounts.data_exports.start()
   print(client.accounts.data_exports.retrieve(export.id).step)    # e.g. manifests, then done

``start()`` returns the export that is already in progress, if there is one. The platform refuses
an export with a 429, a ``RateLimitError`` whose message says why, when the user has no email
address or has started too many exports today. ``start()`` is never retried, whatever the client's
``max_retries``.

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

The platform serves proxies when ``SMARTER_APP_PROXY_ENABLE`` is true.

Endpoints the SDK does not wrap
-------------------------------

``client.http`` is the SDK's authenticated transport. Use it for an endpoint that the SDK doesn't
wrap yet, with the same retries and errors:

.. code-block:: python

   from smarter.core.typing import SmarterJsonType

   data = client.http.request("GET", "llmhosts/report/", cast_to=SmarterJsonType)
