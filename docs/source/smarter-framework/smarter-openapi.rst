Smarter OpenAPI Contract
========================

The `OpenAPI Specification <https://spec.openapis.org/oas/v3.1.0.html>`__ is the industry standard
for describing a REST API in a machine-readable file: its routes, the parameters and bodies that
each one accepts, its responses and errors, and how to authenticate. Tools read that file to render
interactive documentation, to validate requests and responses, and to generate client libraries in
almost any programming language.

Smarter describes the whole :doc:`Smarter API <smarter-api>` this way, in one OpenAPI 3.1 document,
``openapi.json``. Beside it, the platform publishes a JSON Schema and an example manifest for every
:doc:`SAM <smarter-manifests>` kind. Together, these files are the *contract* between a Smarter
platform and its clients: the :doc:`Smarter CLI <smarter-cli>`, the
:doc:`Smarter Python SDK <smarter-python>`, the :doc:`VS Code Extension <vs-code-extension>`, and
any software that you write yourself.

The document is generated from the platform's own Pydantic models, and the platform's tests check
it against the platform's real responses, so it describes what the platform actually does, not what
someone remembered to write down. See :doc:`apis-and-sdks` for the design that the contract and its
clients share.


Where to Find It
----------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Location
     - What it is
   * - ``https://<your platform>/docs/openapi/``
     - The document, rendered with Swagger UI. The web console's sidebar links to it as
       *OpenAPI Contract*. Its *Try it out* sends requests to the platform that you are reading it on.
       Authorize with ``Token <api key>``.
   * - ``https://<your platform>/docs/openapi.json``
     - The document itself, to generate clients from. Its first server is the platform's own
       ``/api/v1``.
   * - `openapi.json <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/api/v1/contract/openapi.json>`__
     - The committed document, in the platform's repository, at any commit or release tag.
   * - `sam/<Kind>.schema.json <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/api/v1/contract/sam>`__
     - The JSON Schema of each SAM kind, which the cli api also returns at
       ``/api/v1/cli/json-schema/<Kind>/``, and the kind's example manifest,
       ``sam/<Kind>.example.json``.

Every Smarter platform serves the document of its own version, so a client generated from your
platform's ``/docs/openapi.json`` matches that platform exactly.


What It Covers
--------------

The document covers every family of routes under ``/api/v1``:

- **The cli api** (``/api/v1/cli/``): apply, validate, get, describe, delete, deploy, undeploy and
  logs of any resource, its example manifest and JSON Schema, and the platform's status, version,
  and the identity of the api key's user.
- **The chat api**: an LLMClient's configuration, and its prompts, as JSON or as a stream of
  Server-Sent Events.
- **The REST reads** of each resource family, e.g. ``GET /api/v1/llm-clients/``, and the few actions
  that a manifest can't express, such as a Guardrail's dry run, a call to an MCP server's tool, or a
  Vectorstore's documents and search.

The complete list of families, and the few routes that the document leaves out with the reason for
each, are in :doc:`The API Contract <smarter-api/api-contract>`.


Conventions
-----------

A few conventions run through the whole document. Knowing them makes the document, and any client
generated from it, easier to read.

- **OpenAPI 3.1 and JSON Schema 2020-12.** In OpenAPI 3.1, a schema is exactly a JSON Schema, which
  is what Pydantic generates. Nothing is lost in translation.
- **Authentication.** Every operation, except a kind's example manifest and JSON Schema, needs an
  api key in the ``Authorization`` header, as ``Token <api key>`` (the ``ApiKeyAuth`` security
  scheme). See :doc:`Authentication <smarter-api/authentication>`.
- **A server variable.** Every Smarter installation has its own url, so the server's url has a
  ``platform`` variable, e.g. ``https://platform.example.com``. Its default is
  ``https://platform.smarter.sh``.
- **Journaled responses.** Every response of the cli api is journaled: its body has the
  :doc:`Smarter Journal's <smarter-api/smarter-journal>` ``api`` and ``metadata``, beside the
  command's ``data``, a ``message``, or an ``error``.
- **One type for any manifest.** ``SAMManifest`` is a ``oneOf`` of the kinds' schemas, with a
  ``discriminator`` on ``kind``. A generated client gets a discriminated union, in which
  ``kind: "Guardrail"`` narrows a manifest to a Guardrail.
- **Typed streams.** OpenAPI can't type the events of a ``text/event-stream`` response, so the
  document names each event's schema in an ``x-smarter-events`` extension of the stream's media type.
- **Errors.** Each operation's ``default`` response names its error's schema: the journal's error
  envelope for the cli api, the :doc:`Chat API Contract's <smarter-chat/api-contract>` error for the
  chat api, and ``{"detail": "..."}`` for the REST reads.
- **Versions.** The document's ``info.version`` is the api's version, ``v1``, which is also its
  path. A change to the api is a change to the committed document, which you can compare between two
  release tags of the platform.

:doc:`The API Contract <smarter-api/api-contract>` describes each of them in detail.


.. _smarter-openapi-generating-a-client:

Generating a Client
-------------------

Any OpenAPI 3.1 or JSON Schema 2020-12 tool can read the contract, from a checkout of the platform
or from a running platform. For example, the TypeScript types of the whole api:

.. code-block:: console

   npx openapi-typescript smarter/smarter/apps/api/v1/contract/openapi.json -o smarter.d.ts
   npx openapi-typescript https://platform.example.com/docs/openapi.json -o smarter.d.ts

The Python SDK copies the contract from a checkout of the platform, at a commit or a release tag
(``make contracts SMARTER_REF=v0.20.0``), and generates its manifest models from the SAM schemas
with datamodel-code-generator (``make sam-models``). Its tests parse every kind's committed example
with its generated model, and check that every cli request that it sends is an operation of
``openapi.json``. No running platform is needed. See
:doc:`Developing the SDK <smarter-python/development>`.

Some generators read only OpenAPI 3.0. oapi-codegen, for Go, is one of them: it rejects the 3.1
forms of ``exclusiveMinimum`` and ``exclusiveMaximum``. For those, generate types from the SAM
schemas directly, or use a generator that supports 3.1.


The Swagger and Redoc Pages
---------------------------

Every platform also has *Swagger* (``/docs/swagger/``) and *Redoc* (``/docs/redoc/``) pages, which
are a different thing. drf-yasg generates them from the platform's views, in OpenAPI 2, for every
endpoint of the platform, including the REST writes, but with untyped request and response bodies.
Use them to explore. Generate clients from ``openapi.json``. See
:doc:`API Documentation <smarter-api/documentation>`.


Changing the Contract
---------------------

The contract is code, in :mod:`smarter.apps.api.v1.contract`. If you work on the platform, and you
change a SAM model, a response, or a route that the document covers, run ``make api-contract`` and
commit the regenerated files. :doc:`The API Contract <smarter-api/api-contract>` explains what
generates each file, and the tests that keep it current.
