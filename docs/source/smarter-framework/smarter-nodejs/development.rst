Developing the SDK
==================

The SDK's source is `github.com/smarter-sh/smarter-nodejs <https://github.com/smarter-sh/smarter-nodejs>`__.
It follows the platform's practices and :doc:`architecture decisions <../../adr>`, and the
`Python SDK <https://docs.smarter-python.smarter.sh/project/contributing.html>`__, which is the reference implementation: the same
features, the same tests, the same recorded responses, the same pre-commit hooks, semantic
versioning and conventional commits. Its own decisions are recorded in its ``doc/adr/`` folder,
numbered as the Python SDK's, and its Agent Skills in ``skills/`` describe how it is developed, for
people and for AI coding agents.

.. code-block:: console

   git clone https://github.com/smarter-sh/smarter-nodejs.git
   cd smarter-nodejs
   make init                     # the dependencies, and the pre-commit hooks
   make test                     # the unit tests
   make coverage                 # with a coverage report
   npm run typecheck && npm run lint

Tests
-----

The **unit tests** run with `Vitest <https://vitest.dev>`__, and never reach a platform: a ``fetch``
double answers every request, with sanitized copies of real platform responses, the same files as
the Python SDK's. They run in CI on every supported Node.js version, which also checks that coverage
stays at 90% or more.

The **live tests** check the SDK against a running platform. They validate every schema against
real responses, including a ``describe`` of a real resource of every kind, validated as its SAM
type. They prompt an LLMClient, which makes billable LLM requests, and they never deploy anything.

.. code-block:: console

   SMARTER_BASE_URL=http://localhost:9357 SMARTER_API_KEY=<api key> make test-live

Releases
--------

The SDK is released as the `Smarter Chat <https://www.npmjs.com/package/@smarter.sh/ui-chat>`__
component is. semantic-release versions it from its conventional commits on each push to ``main``,
and as a prerelease on each push to ``alpha`` or ``beta``: it writes the version to ``package.json``
and ``src/version.ts``, adds the release notes to ``CHANGELOG.md``, tags the commit and creates a
GitHub release. It does not publish to npm. A maintainer publishes a release on ``main`` to the
``@smarter.sh`` scope of the public npm registry with ``make release``, which runs the tests, builds
the package and runs ``npm publish --access public``.

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
     - ``make contracts``, then the SAM types and schemas, generated from the SAM JSON Schemas.
   * - ``npm run reference``
     - The SDK's :doc:`API reference <reference>` pages in the platform's documentation.

When the platform changes a contract or a manifest kind, refresh, run the tests, and fix what they
find. The tests also fail when the platform publishes an API operation that the SDK doesn't call.

The SDK's API reference
-----------------------

Sphinx can't read TypeScript, so the reference pages are generated from the SDK's TSDoc comments:
TypeDoc reads them, and a script writes them as Sphinx's built-in JavaScript domain directives.
Don't edit them: change the doc comment, and regenerate.
