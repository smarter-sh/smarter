The API Contract
================

The Smarter API's contract is published as two kinds of machine-readable files, so that clients in any
language can be generated from it rather than written by hand:

- a **JSON Schema and an example manifest for every SAM kind**, which describe the manifests that
  the API accepts and returns, and
- an **OpenAPI 3.1 document** of the apis that the :doc:`Smarter CLI <../smarter-cli>` and the
  :doc:`Python <../smarter-python>`, :doc:`Node.js <../smarter-nodejs>` and
  :doc:`Go <../smarter-golang>` SDKs call.

Both are generated from the platform's Pydantic models, so they can't drift from what the platform
actually does. This page is the technical reference, written for SDK authors and for backend
developers. For an introduction, see :doc:`Smarter OpenAPI Contract <../smarter-openapi>`, and for the
design goals that the contract and its clients share, :doc:`Smarter APIs, SDKs and Integrations <../apis-and-sdks>`. If you change a SAM
model, the :doc:`journal's <smarter-journal>` response envelope, the
:doc:`chat contract <../smarter-chat/api-contract>`, or a route that the document covers, read this
page first.

The document covers every family of routes of ``/api/v1``, each one typed by Pydantic models and
tested against the platform's real responses:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Family
     - Routes
   * - The cli api
     - Every route of ``/api/v1/cli/``: apply, validate, get, describe, delete, example-manifest,
       json-schema, deploy, undeploy, logs, status, version, whoami, resources, and the cli's
       prompt and prompt configuration.
   * - The chat api
     - ``/api/v1/llm-clients/{id}/config/`` and ``/api/v1/llm-clients/{id}/prompt/``, as JSON and as a
       stream of Server-Sent Events.
   * - The LLMClients' REST reads
     - ``GET /api/v1/llm-clients/``, an LLMClient, and its plugins, api keys, custom domains and
       built-in functions, as lists and one by one.
   * - The Guardrails' REST reads
     - ``GET /api/v1/guardrails/``, a Guardrail, its latest events, and ``POST .../evaluate/``, a dry
       run of a Guardrail on a text.
   * - The Secrets' REST reads
     - ``GET /api/v1/secrets/`` and a Secret: their metadata, never their values.
   * - The MCPClients' REST reads
     - ``GET /api/v1/mcpclients/``, an MCPClient, its tools, ``POST .../refresh/``, which reconnects
       to its MCP server, and ``POST .../tools/{tool_name}/``, which calls a tool.
   * - The vectorstores' REST api
     - ``GET /api/v1/vectorstores/``, a vectorstore, its status, documents and snapshots, and their
       maintenance: deploy and undeploy, add documents (text, a url, or files as
       ``multipart/form-data``), remove one, search, take a snapshot, and restore one.
   * - The LLMHosts' REST api
     - ``GET /api/v1/llmhosts/``, an LLMHost, its status, logs and deployment plan, a report of the
       user's LLMHosts, model discovery and a drafted manifest, and deploy and undeploy.
   * - The plugins' REST reads
     - ``GET /api/v1/plugins/``, the user's plugins' metadata, and ``GET /api/v1/plugins/{plugin_id}/``,
       a plugin's manifest, which the platform serves only while its ``ALLOW_API_GET`` switch is on.
   * - The Providers' REST reads
     - ``GET /api/v1/providers/``, a Provider by name, its models, and one of its models.
   * - The Proxies' list
     - ``GET /api/v1/proxy/``. A Proxy's passthrough is its provider's api, which Smarter does not
       describe.
   * - The accounts' REST reads
     - ``GET /api/v1/accounts/``, an account, and the users, user profiles and account contacts, as
       lists and one by one.
   * - The prompt history
     - ``GET /api/v1/prompts/history/prompt/``, the chat sessions, their ``tool-calls/`` and their
       ``plugin-usage/``, as lists and one by one.
   * - The Smarter Journal
     - ``GET /api/v1/journal/``, one page of the journal's entries, and an entry by its key.
   * - The Orchestrators' and Vectorsearches' REST reads
     - ``GET /api/v1/orchestrators/`` and ``GET /api/v1/vectorsearches/``, and one by its id or hashed
       id.

The few routes that the document leaves out are listed in
:data:`~smarter.apps.api.v1.contract.openapi.UNDOCUMENTED_ROUTES`, each with the reason: web console
actions, whose clients use manifests instead, passthroughs to LLM providers' own apis, and routes
that aren't implemented yet. The families that it leaves out, the views that the platform's unit
tests call, and the :doc:`Smarter Project MCP server <../../smarter-platform/smarter-project-mcp-server>`,
whose protocol the Model Context Protocol specification defines, are listed in
:data:`~smarter.apps.api.v1.contract.openapi.UNDOCUMENTED_URLCONFS`.

Every Smarter platform serves its document, at ``/docs/openapi.json``, and renders it with
`Scalar <https://github.com/scalar/scalar>`__, which the platform ships in its static files, at
``/docs/openapi/``, which the web console's sidebar links to as *OpenAPI Contract*. The page calls
none of Scalar's hosted services. The served document lists the platform's own ``/api/v1`` as its
first server, so that the page's *Test Request* sends requests to the platform that you are
reading it on. Authorize with an api key, as ``Token <api key>``.


Where the Contract Lives
------------------------

The contract is code, in :mod:`smarter.apps.api.v1.contract`:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Module or file
     - Role
   * - :mod:`~smarter.apps.api.v1.contract.sam`
     - The JSON Schema of each SAM kind, from the Pydantic model that the kind's broker validates
       manifests with, and the kind's example manifest, rendered by the cli's example-manifest view.
   * - ``sam/<Kind>.schema.json``
     - The committed schemas, one per kind. Each is exactly the ``data`` of the cli's
       ``json-schema/<Kind>/`` response.
   * - ``sam/<Kind>.example.json``
     - The committed example manifests, one per kind: the ``data`` of the cli's
       ``example-manifest/<Kind>/`` response, without its read-only ``status``, whose timestamps
       change on every request.
   * - :mod:`~smarter.apps.api.v1.contract.models`
     - Pydantic models of the cli responses whose data is not a manifest (apply, validate, get,
       status, version, whoami, resources, prompt), and of the OpenAPI document itself. The views
       build their responses from them.
   * - :mod:`~smarter.apps.api.v1.contract.openapi`
     - Assembles the OpenAPI document from the SAM models, the
       :mod:`journal contract <smarter.lib.journal.contract.models>`, the
       :doc:`chat contract <../smarter-chat/api-contract>` and the models above.
   * - ``openapi.json``
     - The committed OpenAPI document.

After changing any of the models, or a route that the document covers, run ``make api-contract``. It runs
``manage.py export_api_contract`` in the ``smarter-app`` container, copies the files back to your
working tree, and you commit them.

The tests make the contract hard to break by accident. They fail when:

- a committed schema, example, or ``openapi.json``, is out of date,
- a committed schema differs from what the ``json-schema`` command returns,
- a kind's example manifest isn't valid under its own schema,
- a real response isn't valid under the document's schema for it: of the cli (apply, get,
  describe, delete, validate, example-manifest, json-schema, status, version, whoami, resources,
  prompt/config, prompt, and an error), and of the chat api (a configuration, a prompt as JSON, every
  event of a streamed prompt, and an error). The prompt tests make real, billable LLM requests,
- a route of a covered family, a urlconf in
  :data:`~smarter.apps.api.v1.contract.openapi.DOCUMENTED_URLCONFS`, is neither in the document
  nor listed, with a reason, in :data:`~smarter.apps.api.v1.contract.openapi.UNDOCUMENTED_ROUTES`,
- a family of routes that ``/api/v1`` mounts is neither covered nor listed, with a reason, in
  :data:`~smarter.apps.api.v1.contract.openapi.UNDOCUMENTED_URLCONFS`.


What the Document Describes
---------------------------

The cli api
~~~~~~~~~~~

Every cli command is a ``POST``. Each one has a ``200`` response with the command's data, and a
``default`` response for errors. A request carries an api key in its ``Authorization`` header, as
``Token <api key>``. ``example-manifest`` and ``json-schema`` are public, and need no key. The
operations are tagged ``manifests``, ``deployment``, ``platform`` and ``chat``.

Every response is *journaled*. Its body has the journal's ``api`` and ``metadata``, beside the
command's ``data``, a human-readable ``message``, or an ``error``:

.. code-block:: json

   {
     "data": {"apiVersion": "smarter.sh/v1", "kind": "Guardrail", "name": "pii_redactor"},
     "message": "Guardrail pii_redactor applied successfully",
     "api": "smarter.sh/v1",
     "metadata": {"command": "apply", "thing": "Guardrail"}
   }

A manifest of any kind is ``SAMManifest``: a ``oneOf`` of the kinds' schemas, with a
``discriminator`` on ``kind``. The SAM models declare ``kind`` as a plain string, so in the document
each kind's schema adds ``"const": "<Kind>"`` to it. A generated client gets a discriminated union,
for example a TypeScript type in which ``kind: "Guardrail"`` narrows the manifest to a Guardrail.

The server url has a ``platform`` variable, because every Smarter installation has its own, for
example ``https://platform.example.com``. Its default is ``https://platform.smarter.sh``.

``status`` types the platform's compute and Redis, but not its Kubernetes cluster, whose
description depends on the infrastructure provider.

The two chat routes need a ``uid`` query parameter, a unique identifier of the client, under which
the platform caches the client's chat session, so that the next prompt continues it.
``new_session=true`` starts a new one. ``prompt/config/<name>/`` returns the
:doc:`Chat API Contract's <../smarter-chat/api-contract>` version 2 configuration.
``prompt/<name>/`` takes ``{"prompt": "..."}``, and returns the request that it sent to the
LLMClient beside the LLMClient's response: the chat contract's version 1 response, whose ``body``
is decoded from a JSON string into the completion.

The chat api
~~~~~~~~~~~~

The chat api is what Smarter Chat and the SDKs call to chat with an LLMClient. Its requests and
responses are the :doc:`Chat API Contract's <../smarter-chat/api-contract>`, version 2, which the
``X-Smarter-Capabilities: chat-contract-v2`` header asks for, and which is also the default. ``{id}``
is the LLMClient's numeric id or its hashed id.

- ``POST /llm-clients/{id}/config/`` takes ``{"session_key": ...}``, empty for a new session, and
  returns the chat's configuration, whose ``session_key`` identifies the session.
- ``POST /llm-clients/{id}/prompt/`` takes ``{"session_key": ..., "messages": [...]}``, and returns
  the messages that the prompt added. A failed prompt returns the same response with an ``error``,
  and the LLM provider's http status.

A client that sends ``Accept: text/event-stream`` receives the prompt as Server-Sent Events:
``progress`` events while it runs, then one ``result`` event, whose ``response`` is the JSON that a
non-streaming client receives. OpenAPI 3.1 can't type the events of a stream, so the document names
their schemas in an ``x-smarter-events`` extension of the stream's media type:

.. code-block:: json

   "text/event-stream": {
     "schema": {"type": "string", "description": "Server-Sent Events: ..."},
     "x-smarter-events": {
       "progress": {"$ref": "#/components/schemas/PromptChatApiProgressEvent"},
       "result": {"$ref": "#/components/schemas/PromptChatApiProgressResult"}
     }
   }

The REST reads
~~~~~~~~~~~~~~

The REST api's views read and write each resource family's rows, e.g. ``/api/v1/llm-clients/``. The
document publishes only their reads, the ``GET`` requests. Clients write through the cli api's
manifests, which the brokers validate, as the SDKs do.

Their responses are built from each app's contract models, e.g.
:mod:`smarter.apps.llmclient.contract.models`, which are models of the rows, built from them by
``from_model()``. Shared parts live with the app that owns them: a resource's owner in
:mod:`smarter.apps.account.contract.models`, and a plugin's metadata in
:mod:`smarter.apps.llmtool.contract.models`. The models describe the JSON that the views returned
before they were modeled, which clients already read, with two corrections:

- ``canDelete`` is computed for the requesting user, for every family. The
  views called their serializers without the request, so it was always false.
- An LLMClient's api key is its token's public ``key_id``. It was the token's primary key, its digest.
- A chat session is read by the session's id, like the list's rows. It was a different row's id, a
  PromptHistory's.

The LLMClients', Secrets', accounts' and :doc:`journal's <smarter-journal>` REST views require an api
key of a superuser, and refuse other users with a 403. Other users read their resources with the cli
api's ``get`` and ``describe``. The other families' views accept any api key, and return only what its
user may read; their actions that change something require the user to own the resource. Each
operation's description says which.

The accounts' reads (``/accounts/``) return the accounts, users, user profiles (each user's membership
of an account) and account contacts. The prompt history (``/prompts/history/``) returns the chat
sessions, newest first, and the tool calls and plugin usage of each. A session holds a user's
conversation, so the history includes only the sessions whose user the requesting user may manage:
their own, their account's users' for an account admin, and every one for a superuser. The journal's
list is paged: ``page``, ``page_size``, ``search`` and ``ordering`` select the page, and its
``pagination`` describes it. The Proxies'
and vectorstores' routes exist only when the platform enables them (``SMARTER_ENABLE_PROXY``,
``SMARTER_ENABLE_VECTORSTORE``).

A Guardrail's events, the prompt history, and a catalog's models in an LLMHost discovery, keep the
snake_case keys that they had, e.g. ``guardrail_name``, ``session_key`` and ``parameter_count``, unlike the rest of the REST api, which is
camelCase, because clients already read them.

Besides the reads, the document publishes the actions that the SDKs use: a Guardrail's dry run,
which changes nothing, an MCPClient's reconnection and tool call, and a vectorstore's maintenance. A
tool runs on the MCP server, and may change what the server manages, so only the MCPClient's owner may
call it. Deploying a vectorstore or an LLMHost creates billable infrastructure. Work that continues in the background
answers ``202``, e.g. a deployment, or documents that are queued to be loaded, and a new snapshot
answers ``201``.

Errors
~~~~~~

The cli api's errors are the journal's error response. The chat api's are the chat contract's
``PromptChatApiErrorResponse``. The REST reads' are Django REST framework's ``{"detail": "..."}``,
``RestApiErrorResponse``. A failed connection to an MCP server adds the MCPClient's connection status
beside its ``detail``. Each operation's ``default`` response names its error's schema.

Clients
-------

The live OpenAPI Contract page, and how to generate a client from ``openapi.json``, are on the
user-facing :doc:`Smarter OpenAPI Contract <../smarter-openapi>` page.

The SDKs, the cli and the VS Code extension (smarter-vscode-yaml) each keep a pinned copy of these
files, which their own tests check their code against. Each one copies it with its own
``make contracts SMARTER_REF=<release tag>``. Every week, the platform's *API Contract Sync*
workflow (``.github/workflows/apiContractSync.yml``) syncs each repository's ``alpha`` branch with
the platform's latest stable release, and runs that repository's unit tests before and after the
sync. When a copy is out of date, it opens an issue in that repository, labeled ``api-contract``,
and a pull request from its ``api-contract-sync`` branch with the sync as one commit. The pull
request is a draft when the tests fail after the sync, because the release changed the contract in a
way that needs work in the client. Later runs update the same issue and pull request, and close both
once the copy is current. Each run posts one message to the #general Slack channel: the
repositories that are out of date, or a clean bill of health.


Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   code/contract
