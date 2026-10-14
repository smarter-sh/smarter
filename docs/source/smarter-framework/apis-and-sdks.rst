Smarter APIs and SDKs
=====================

Everything that you can do in the :doc:`web console <../smarter-platform/smarter-web-console>`, you
can also do from your own software. This section documents the pieces that make that possible, and
the design that they share.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Piece
     - What it is
   * - :doc:`Smarter API Manifests (SAM) <smarter-manifests>`
     - The resource model. A YAML or JSON document that declares what a resource (an LLMClient, a
       Plugin, a Guardrail, a Secret, ...) should be. Every client creates and changes resources by
       applying manifests.
   * - :doc:`Smarter API <smarter-api>`
     - The REST API that every client calls, under ``/api/v1/``. It applies manifests, reads
       resources, and chats with LLMClients.
   * - :doc:`Smarter OpenAPI Contract <smarter-openapi>`
     - The machine-readable description of the Smarter API: an OpenAPI 3.1 document, and a JSON
       Schema and example manifest for every SAM kind. Clients in any language are generated from
       it.
   * - :doc:`Smarter CLI <smarter-cli>`
     - A command-line program, like ``kubectl``, for people at a terminal and for shell scripts.
   * - :doc:`Smarter Python SDK <smarter-python>`
     - A Python library, ``pip install smarter-api``, for applications, services, notebooks, tests
       and automation. The reference implementation of every Smarter SDK.
   * - :doc:`Smarter Node.js SDK <smarter-nodejs>`
     - A TypeScript library for Node.js, ``npm install @smarter.sh/api``, for web back ends, serverless
       functions, services and automation.
   * - :doc:`Smarter Go SDK <smarter-golang>`
     - A Go module, ``go get github.com/smarter-sh/smarter-golang``, for services, Kubernetes
       operators, infrastructure tooling and automation.
   * - :doc:`VS Code Extension <vs-code-extension>`
     - The editor for manifests: validation as you type, completion and help from the same JSON
       Schemas, and the CLI's validate, apply and deploy commands.

The three ideas are layered. SAM says *what* a resource is, the Smarter API is *how* a client asks
for it, and the OpenAPI contract is the *written agreement* between the platform and its clients.
The CLI and the SDKs are clients of that agreement, and nothing else: none of them has access to the
platform that your own software doesn't have.

Smarter's SDKs follow the same design, whatever their language. The Python SDK was the first of
them, and is the reference implementation: the Node.js and Go SDKs have its features, resources,
verbs and errors, number their architecture decisions as it does, and are tested against the same
recorded responses of the platform.


Design Goals
------------

The goals below are common to the Smarter API and to every official client. They are what you can
rely on when you integrate with Smarter, and they are the requirements for anyone who writes a new
SDK.

One source of truth: Pydantic models
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every request and response of the Smarter API is a `Pydantic <https://docs.pydantic.dev/>`__ model
in the platform's code, and the platform builds its responses from those models
(:doc:`ADR-031 <../adr/031-pydantic-over-json>`). A manifest kind's model validates every manifest
of that kind (:doc:`ADR-005 <../adr/005-manifests>`), and a resource's REST model is built from its
database row, with exactly the row's fields.

Nothing about the API is described by hand. The OpenAPI document and the SAM JSON Schemas are
generated from the same models, and a client's types are generated from those files. A field that
the platform adds, renames or removes therefore changes the contract, then the clients' types, in
that order, and never silently.

A contract that can't drift
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The contract is committed to the platform's repository, and the platform's tests fail when it is
out of date, or when a real response of the platform doesn't validate against it. A breaking change
to the API is therefore visible as a diff of ``openapi.json`` or of a ``sam/<Kind>.schema.json``,
in the same pull request as the change that caused it. See
:doc:`The API Contract <smarter-api/api-contract>`.

The SDKs check the other side. Each SDK copies the contract from the platform, at a commit or a
release tag, and its own tests fail when it sends a request that the contract doesn't describe, or
when its models no longer read the contract's examples.

Declarative writes, typed reads
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Clients create, change and delete resources by applying :doc:`manifests <smarter-manifests>`, which
the :doc:`brokers <smarter-broker-model>` validate before anything is changed. The same manifest
gives the same result whether it is applied from the CLI, an SDK, a CI/CD job or the web console,
and it can be kept in version control and reviewed like code.

The REST API publishes typed *reads* of each resource family, and the few *actions* that a manifest
can't express, such as a Guardrail's dry run, a call to an MCP server's tool, or adding documents to
a Vectorstore. It doesn't publish a second, imperative way to write a resource.

Same vocabulary in every language
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each SDK is idiomatic in its own language: snake_case in Python, camelCase in TypeScript, exported
types in Go. Its vocabulary is the platform's: the same resource kinds, and the same verbs as the
CLI (``apply``, ``validate``, ``get``, ``describe``, ``delete``, ``deploy``, ``undeploy``,
``logs``). Someone who knows ``smarter apply -f guardrail.yaml`` can guess
``client.manifests.apply("guardrail.yaml")``.

Every SAM kind has a typed model in every SDK, generated from the kind's JSON Schema rather than
written by hand, so a new kind or field reaches every language the same way.

Strict platform, tolerant clients
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The platform is strict about what it accepts and what it returns: its models forbid fields that they
don't declare, so nothing leaves the platform by accident. The clients are tolerant: their models
keep fields that they don't declare yet, so an SDK keeps working when a newer platform adds a field
to a response.

A JSON Schema can't express every business rule that the platform's models apply. An SDK's models
check a manifest's structure, and the platform's ``validate`` command checks the rest.

One credential, one configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Every client authenticates with a Smarter API key, sent as ``Authorization: Token <api key>``, and
can do whatever the key's user can do. See :doc:`Authentication <smarter-api/authentication>`.

The SDKs read the CLI's configuration file, ``~/.smarter/config.yaml``, and the same
``SMARTER_API_KEY`` and ``SMARTER_BASE_URL`` environment variables, so a developer who has run
``smarter configure`` needs no other setup. Every client works with any Smarter platform, not only
``platform.smarter.sh``: yours, on your laptop or on :doc:`Kubernetes <smarter-on-kubernetes>`.

Typed errors
~~~~~~~~~~~~

Every error response of the Smarter API has a documented schema: the
:doc:`Smarter Journal's <smarter-api/smarter-journal>` error envelope for the manifest API, the
:doc:`Chat API Contract's <smarter-chat/api-contract>` error for the chat API, and
``{"detail": "..."}`` for the REST reads. A journaled error names the platform's exception class,
e.g. ``SAMBrokerErrorNotFound``.

The SDKs turn these into one hierarchy of exceptions, or its equivalent in the language, with one
root that catches them all, and a subclass for each HTTP status
(:doc:`ADR-012 <../adr/012-error-handling>`).

Streaming, the same way everywhere
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A prompt can take a while. A client that asks for ``text/event-stream`` receives its progress as
Server-Sent Events, then one result, which is exactly the JSON that a non-streaming client receives.
The SDKs offer both, and :doc:`Smarter Chat <smarter-chat>` uses the same stream.

Testable without a platform
~~~~~~~~~~~~~~~~~~~~~~~~~~~

An SDK's unit tests never reach a platform: they answer its requests with sanitized copies of real
responses, and validate those against the contract. Separate live tests run the SDK against a real
platform. They are the only tests that need an api key, and the only ones that make billable LLM
requests.

The same practices as the platform
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The SDKs are developed the way the platform is: semantic versioning, conventional commits,
pre-commit hooks, docstrings that are published here, the platform's
:doc:`architecture decisions <../adr>`, and Agent Skills that describe how each repository is
developed, for people and for AI coding agents.


Writing an SDK for Another Language
-----------------------------------

Start from the contract, not from the platform's code:

1. Copy ``openapi.json`` and ``sam/*.json`` from
   `smarter/apps/api/v1/contract <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/api/v1/contract>`__,
   at a release tag, with a command that can refresh them.
2. Generate the SAM models from the SAM JSON Schemas, and the API's types from ``openapi.json``.
   Prefer a generator that reads OpenAPI 3.1; see
   :ref:`smarter-openapi-generating-a-client`.
3. Test that every kind's example manifest parses with its generated model, and that every request
   that the SDK sends is an operation of ``openapi.json``.
4. Follow the design goals above, and the :doc:`Python SDK <smarter-python>` as the reference
   implementation, from its configuration lookup to its exception hierarchy. The
   :doc:`Node.js <smarter-nodejs>` and :doc:`Go <smarter-golang>` SDKs show how its design
   translates into other languages.


.. toctree::
   :maxdepth: 1
   :caption: Smarter APIs and SDKs

   smarter-manifests
   smarter-api
   smarter-openapi
   smarter-cli
   smarter-python
   smarter-nodejs
   smarter-golang
   vs-code-extension
