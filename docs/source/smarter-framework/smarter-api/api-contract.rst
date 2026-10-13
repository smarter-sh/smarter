The API Contract
================

The Smarter API's contract is published as two kinds of machine-readable files, so that clients in any
language can be generated from it rather than written by hand:

- a **JSON Schema and an example manifest for every SAM kind**, which describe the manifests that
  the API accepts and returns, and
- an **OpenAPI 3.1 document** of the cli api (``/api/v1/cli/``), the api that the
  :doc:`Smarter CLI <../smarter-cli>` and the :doc:`Smarter Python SDK <../smarter-python>` call to
  apply, get, describe, validate and delete resources, and to chat with LLMClients.

Both are generated from the platform's Pydantic models, so they can't drift from what the platform
actually does. They are written for SDK authors, and for backend developers. If you change a SAM
model, the :doc:`journal's <smarter-journal>` response envelope, or a cli command, read this page
first.


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

After changing any of the models, or a cli route, run ``make api-contract``. It runs
``manage.py export_api_contract`` in the ``smarter-app`` container, copies the files back to your
working tree, and you commit them.

The tests make the contract hard to break by accident. They fail when:

- a committed schema, example, or ``openapi.json``, is out of date,
- a committed schema differs from what the ``json-schema`` command returns,
- a kind's example manifest isn't valid under its own schema,
- a real response of the cli (apply, get, describe, delete, validate, example-manifest,
  json-schema, status, version, whoami, resources, prompt/config, prompt, and an error) isn't valid
  under the document's schema for it. The prompt test makes a real, billable LLM request,
- a new cli route is neither in the document nor listed, with a reason, in
  :data:`~smarter.apps.api.v1.contract.openapi.UNDOCUMENTED_CLI_ROUTES`.


What the Document Describes
---------------------------

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
