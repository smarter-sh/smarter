The API Contract
================

The Smarter API's contract is published as two kinds of machine-readable files, so that clients in any
language can be generated from it rather than written by hand:

- a **JSON Schema and an example manifest for every SAM kind**, which describe the manifests that
  the API accepts and returns, and
- an **OpenAPI 3.1 document** of the apis that the :doc:`Smarter CLI <../smarter-cli>` and the
  :doc:`Smarter Python SDK <../smarter-python>` call.

Both are generated from the platform's Pydantic models, so they can't drift from what the platform
actually does. They are written for SDK authors, and for backend developers. If you change a SAM
model, the :doc:`journal's <smarter-journal>` response envelope, the
:doc:`chat contract <../smarter-chat/api-contract>`, or a route that the document covers, read this
page first.

The document grows one family of routes at a time, each one typed by Pydantic models and tested
against the platform's real responses. It covers:

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

The other routes of a covered family are listed in
:data:`~smarter.apps.api.v1.contract.openapi.UNDOCUMENTED_ROUTES`, each with the reason that it is
left out. Until a family is covered, a client reads its resources from the REST api's own views,
described only by the live Swagger page, untyped.


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
  nor listed, with a reason, in :data:`~smarter.apps.api.v1.contract.openapi.UNDOCUMENTED_ROUTES`.


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
:mod:`smarter.apps.plugin.contract.models`. The models describe the JSON that the views returned
before they were modeled, which clients already read, with two corrections:

- ``canDelete`` is computed for the requesting user, for every family. The
  views called their serializers without the request, so it was always false.
- An LLMClient's api key is its token's public ``key_id``. It was the token's primary key, its digest.

The LLMClients' and Secrets' REST views require an api key of a superuser, and refuse other users with
a 403. Other users read their resources with the cli api's ``get`` and ``describe``. The other
families' views accept any api key, and return only what its user may read; their actions that change
something require the user to own the resource. Each operation's description says which. The Proxies'
and vectorstores' routes exist only when the platform enables them (``SMARTER_ENABLE_PROXY``,
``SMARTER_ENABLE_VECTORSTORE``).

A Guardrail's events, and a catalog's models in an LLMHost discovery, keep the snake_case keys that
they had, e.g. ``guardrail_name`` and ``parameter_count``, unlike the rest of the REST api, which is
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

The Swagger page
~~~~~~~~~~~~~~~~

The live Swagger and Redoc pages (``/docs/swagger/`` and ``/docs/redoc/``) are a different thing.
drf-yasg generates them from the views, in OpenAPI 2, for every api of the platform, but with
untyped request and response bodies. Generate clients from ``openapi.json`` instead.


Generating a Client
-------------------

Any OpenAPI 3.1 or JSON Schema 2020-12 tool can read the contract. For example, the TypeScript
types of the whole cli api:

.. code-block:: console

   npx openapi-typescript smarter/smarter/apps/api/v1/contract/openapi.json -o smarter.d.ts

The Python SDK copies the contract from a checkout of the platform, at a commit or a release tag
(``make contracts SMARTER_REF=v0.20.0``), and generates its manifest models from the SAM schemas
with datamodel-code-generator (``make sam-models``). Its tests parse every kind's committed example
with its generated model, and check that every cli request that it sends is an operation of
``openapi.json``. No running platform is needed.

Some generators read only OpenAPI 3.0. oapi-codegen, for Go, is one of them: it rejects the 3.1
forms of ``exclusiveMinimum`` and ``exclusiveMaximum``. For those, generate types from the SAM
schemas directly, or use a generator that supports 3.1.


Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   code/contract
