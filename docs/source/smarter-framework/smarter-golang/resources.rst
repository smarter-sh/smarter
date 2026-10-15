Resources
=========

Each resource family is a field of the client. Every family that has a REST API can ``List`` its
resources, ``Retrieve`` one by its ``smarter.ID``, and ``Find`` one by name, and every family has the
manifest operations described in :doc:`Manifests <manifests>`. Beyond those, each family has the
actions that its REST API offers. Every method takes a ``context.Context`` first, and a method's
optional arguments are a params struct, which may be ``nil``.

What a user can see and do is decided by the platform: the API key's user reads the resources of
their account, and only a resource's owner may change it. Some endpoints, e.g. the Smarter Journal,
are for superusers only.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Field
     - Resources and actions
   * - ``client.Manifests``
     - Any kind, through the manifest API. See :doc:`Manifests <manifests>`.
   * - ``client.LLMClients``
     - :doc:`LLMClients <../../smarter-resources/smarter-llmclient>`: ``Prompt``, ``Chat``,
       ``Stream``, ``Config``, their ``Plugins``, ``Functions``, ``APIKeys`` and ``CustomDomains``,
       and ``Deploy``. An LLMClient's ``Tools`` list everything that it adds to a prompt: its
       functions, plugins, MCPClients (``MCPClients``) and guardrails (``Guardrails``). See
       :doc:`Prompts and Chat <chat>`.
   * - ``client.Guardrails``
     - :doc:`Guardrails <../../smarter-resources/smarter-guardrail>`: ``Evaluate`` and ``Events``.
   * - ``client.MCPClients``
     - :doc:`MCPClients <../../smarter-resources/smarter-mcpclient>`: ``Tools``, ``Refresh`` and
       ``CallTool``.
   * - ``client.Vectorstores``
     - :doc:`Vectorstores <../../smarter-resources/smarter-vectorstore>`: ``Status``, ``Deploy``,
       ``Documents``, ``AddText``, ``AddURL``, ``AddFiles``, ``DeleteDocument``, ``Search``,
       ``Snapshots``, ``CreateSnapshot`` and ``Restore``.
   * - ``client.LLMHosts``
     - LLMHosts: ``Status``, ``Logs``, ``Plan``, ``Deploy``, ``Undeploy``, ``Report``, ``Discover``
       and ``DiscoverManifest``.
   * - ``client.Secrets``, ``client.Plugins``, ``client.Orchestrators``, ``client.Vectorsearches``
     - Read them, and manage them with manifests. A plugin's manifest kind is its class, e.g.
       ``SqlPlugin``, which ``client.Plugins`` looks up for you. ``Plugins.RetrieveManifest`` reads a
       plugin's manifest by its id.
   * - ``client.Accounts``
     - Accounts, and ``Accounts.Users``, ``Accounts.UserProfiles`` (each user's membership of an
       account) and ``Accounts.Contacts``. Superusers only.
   * - ``client.History``
     - The chat sessions, their tool calls and their plugin uses, newest first: the user's own, their
       account's users' for an account admin, and every one for a superuser.
   * - ``client.Journal``
     - The :doc:`Smarter Journal <../smarter-api/smarter-journal>`, page by page. Superusers only.
   * - ``client.Providers``
     - The LLM providers that the platform is configured for, and their models.
   * - ``client.Proxies``
     - Proxies to LLM providers' own APIs: ``BaseURL`` and ``Request``.
   * - ``client.WhoAmI``, ``Version``, ``Status``, ``Kinds``
     - The API key's user and account, the platform's version and state, and its resource kinds.

Guardrails
----------

Dry-run a Guardrail on a text, e.g. to test a new pattern before you rely on it. Nothing is saved.

.. code-block:: go

   result, err := client.Guardrails.Evaluate(ctx, guardrail.Ref(), "My card is 4111 1111 1111 1111", nil)
   if err != nil {
       return err
   }
   if result.Triggered {
       fmt.Println(result.Disposition, result.Text) // e.g. redacted "My card is [REDACTED]"
   }
   events, err := client.Guardrails.Events(ctx, guardrail.Ref(), &smarter.GuardrailEventsParams{Reviewed: smarter.Ptr(false)})
   if err != nil {
       return err
   }
   for _, event := range events.Events {
       fmt.Println(event.CreatedAt, event.LLMClient, event.Disposition)
   }

MCP clients
-----------

.. code-block:: go

   tools, err := client.MCPClients.Tools(ctx, mcpclient.Ref(), nil)
   if err != nil {
       return err
   }
   for _, tool := range tools.Tools {
       fmt.Println(tool.Name, tool.InputSchema)
   }
   called, err := client.MCPClients.CallTool(ctx, mcpclient.Ref(), "aws___search_documentation", smarter.JSONObject{"search_phrase": "S3"})
   if err != nil {
       return err
   }
   fmt.Println(called.IsError, called.Content)

Only an MCPClient's owner may call its tools.

Vectorstores
------------

.. code-block:: go

   if _, err := client.Vectorstores.AddText(ctx, store.Ref(), "Our refund window is 30 days.", &smarter.AddTextParams{Name: "refunds"}); err != nil {
       return err
   }
   if _, err := client.Vectorstores.AddFiles(ctx, store.Ref(), []string{"handbook.pdf", "policies.docx"}); err != nil {
       return err
   }
   found, err := client.Vectorstores.Search(ctx, store.Ref(), "How long is the refund window?", &smarter.SearchParams{K: 3})
   if err != nil {
       return err
   }
   for _, hit := range found.Results {
       fmt.Println(smarter.Deref(hit.Score), hit.Text)
   }

Documents are split, embedded and loaded asynchronously, and only once the vectorstore is deployed.
The platform serves these endpoints when ``SMARTER_ENABLE_VECTORSTORE`` is true.

LLMHosts
--------

An LLMHost serves an open-weight model on the platform's own cluster. ``Plan`` shows the Kubernetes
resources that ``Deploy`` would create, without creating them. Deploying creates real, billable
infrastructure, which may include GPU nodes.

.. code-block:: go

   models, err := client.LLMHosts.Discover(ctx, &smarter.DiscoverParams{Query: "qwen", Task: "chat", Limit: 5})
   if err != nil {
       return err
   }
   for _, model := range models {
       fmt.Println(model.Repository, smarter.Deref(model.Downloads))
   }
   manifest, err := client.LLMHosts.DiscoverManifest(ctx, "Qwen/Qwen2.5-7B-Instruct", nil)
   if err != nil {
       return err
   }
   if _, err := client.LLMHosts.Apply(ctx, manifest); err != nil {
       return err
   }

Proxies
-------

A Proxy gives authenticated, governed access to an LLM provider's own API: the platform holds the
provider's key, and you use your Smarter API key instead. The easiest client of a proxy is the
provider's own SDK, with ``client.Proxies.BaseURL("openai")`` as its base url and
``client.APIKey()`` as its api key. ``client.Proxies.Request`` sends one request through a proxy:

.. code-block:: go

   completion, err := client.Proxies.Request(ctx, "openai", "chat/completions", &smarter.ProxyRequestParams{
       JSON: smarter.JSONObject{"model": "gpt-4o-mini", "messages": []any{map[string]any{"role": "user", "content": "Hi"}}},
   })

The platform serves proxies when ``SMARTER_ENABLE_PROXY`` is true.

Endpoints the SDK does not wrap
-------------------------------

``client.Do`` sends a request to an endpoint that the SDK doesn't wrap yet, with the same
authentication, retries and errors, and decodes its JSON into your struct:

.. code-block:: go

   var report smarter.LLMHostReport
   err := client.Do(ctx, http.MethodGet, "llmhosts/report/", nil, &report)
