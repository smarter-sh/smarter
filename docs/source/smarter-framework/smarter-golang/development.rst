Developing the SDK
==================

The SDK's source is `github.com/smarter-sh/smarter-golang <https://github.com/smarter-sh/smarter-golang>`__.
It follows the platform's practices and :doc:`architecture decisions <../../adr>`, the
:doc:`Python SDK <../smarter-python/development>`, which is the reference implementation, and the
:doc:`Smarter CLI <../smarter-cli>`, which is also written in Go: the same features, the same tests,
the same recorded responses, the CLI's Go hooks (gofmt, go vet, goimports, golangci-lint),
semantic versioning and conventional commits. Its own decisions are recorded in its ``doc/adr/``
folder, numbered as the Python SDK's, and its Agent Skills in ``skills/`` describe how it is
developed, for people and for AI coding agents.

.. code-block:: console

   git clone https://github.com/smarter-sh/smarter-golang.git
   cd smarter-golang
   make init                     # the release tooling, and the pre-commit hooks
   make test                     # the unit tests, with the race detector
   make coverage                 # with coverage
   make vet                      # go vet and golangci-lint

Tests
-----

The **unit tests** never reach a platform: a ``RoundTripper`` answers every request, with sanitized
copies of real platform responses, the same files as the Python SDK's. The package's runnable
examples, which pkg.go.dev shows, are tests too. They run in CI on every supported Go release,
which also checks that coverage stays at 90% or more.

The **live tests** check the SDK against a running platform. They decode real responses into every
struct, including a ``Describe`` of a real resource of every kind, decoded into its SAM struct.
They prompt an LLMClient, which makes billable LLM requests, and they never deploy anything.

.. code-block:: console

   SMARTER_BASE_URL=http://localhost:9357 SMARTER_API_KEY=<api key> make test-live

Keeping in step with the platform
---------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Command
     - What it refreshes
   * - ``make contracts``
     - The platform's :doc:`api contract <../smarter-api/api-contract>`, from a checkout of the
       platform beside the SDK (``../smarter``): the JSON Schema and example manifest of every SAM
       kind, the api's OpenAPI document, and the chat and journal contracts' JSON Schemas and
       examples. ``SMARTER_REF=<ref>`` reads them at a commit or tag, e.g. ``origin/main``.
   * - ``make sam-models``
     - ``make contracts``, then the ``sam`` package, generated from the SAM JSON Schemas by the
       SDK's own generator, ``internal/cmd/samgen``.

When the platform changes a contract or a manifest kind, refresh, run the tests, and fix what they
find. The tests also fail when the platform publishes an API operation that the SDK doesn't call.
The API reference is pkg.go.dev, which a release tag updates.

Releases
--------

semantic-release versions the SDK from its conventional commit messages on ``main``. It writes the
version into ``version.go``, tags the commit ``vX.Y.Z``, which is the Go module's version, and
creates a GitHub Release. The ``Build-Release GitHub`` workflow then builds and tests the tag on
Linux, macOS and Windows, asks the Go module proxy to fetch it and pkg.go.dev to index it, and
checks that a new module can import it with ``go get``. Run that workflow by hand to publish a tag
again. A published version can't be deleted or replaced, because the module proxy caches it: retract
a bad one with a ``retract`` directive in ``go.mod``, in a new release.
