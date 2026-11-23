Smarter SDKs
============

The Smarter SDKs give your own software typed, complete access to a Smarter platform, yours or
``platform.smarter.sh``, on your laptop or on
:doc:`Kubernetes </smarter-framework/smarter-on-kubernetes>`. Each one covers every resource kind
through the same :doc:`manifest API </smarter-framework/smarter-api/cli>` as the
:doc:`Smarter CLI </smarter-framework/smarter-cli>`, prompts and streamed chats with
:doc:`LLMClients </smarter-resources/smarter-llmclient>`, each resource's own actions, and typed
models of every :doc:`manifest </smarter-framework/smarter-manifests>` kind.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - SDK
     - What it is
   * - :doc:`Smarter Python SDK <smarter-sdks/smarter-python>`
     - A Python library, ``pip install smarter-api``, for applications, services, notebooks, tests
       and automation. The reference implementation of every Smarter SDK.
   * - :doc:`Smarter Node.js SDK <smarter-sdks/smarter-nodejs>`
     - A TypeScript library for Node.js, ``npm install @smarter.sh/api``, for web back ends, serverless
       functions, services and automation.
   * - :doc:`Smarter Go SDK <smarter-sdks/smarter-golang>`
     - A Go module, ``go get github.com/smarter-sh/smarter-golang``, for services, Kubernetes
       operators, infrastructure tooling and automation.

The SDKs follow the same design, whatever their language. The Python SDK was the first of them,
and is the reference implementation: the Node.js and Go SDKs have its features, resources, verbs
and errors, number their architecture decisions as it does, and are tested against the same
recorded responses of the platform. Each is a client of the
:doc:`OpenAPI contract </smarter-framework/smarter-openapi>`, and nothing else, so none of them has
access to the platform that your own software doesn't have.

They authenticate with a Smarter API key, and read the CLI's configuration file,
``~/.smarter/config.yaml``, and the same ``SMARTER_API_KEY`` and ``SMARTER_BASE_URL`` environment
variables, so a developer who has run ``smarter configure`` needs no other setup. The design goals
that they share with the Smarter API, and how to write an SDK for another language, are in
:doc:`Smarter APIs, SDKs and Integrations </smarter-framework/apis-and-sdks>`.


.. toctree::
   :maxdepth: 1
   :caption: SDKs

   smarter-sdks/smarter-python
   smarter-sdks/smarter-nodejs
   smarter-sdks/smarter-golang
