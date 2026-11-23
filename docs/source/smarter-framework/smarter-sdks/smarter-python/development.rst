Developing the SDK
==================

Bug reports, questions and pull requests are welcome. Please
`open an issue <https://github.com/smarter-sh/smarter-python/issues>`__ before starting on a larger
change, so that we can agree on its design first.

The SDK follows the platform's practices and
:doc:`architecture decisions </adr>`: the same pre-commit hooks,
reStructuredText docstrings, semantic versioning and conventional commits. Its own decisions are
recorded in its `architecture decision records <https://docs.smarter-python.smarter.sh/adr.html>`__, and the Agent Skills in its ``skills/`` folder describe how it is
developed, for people and for AI coding agents.

Development setup
-----------------

.. code-block:: console

    $ git clone https://github.com/smarter-sh/smarter-python.git
    $ cd smarter-python
    $ make init

``make init`` creates the repository's own virtual environment, ``venv/``, with the development
requirements, and installs the pre-commit hooks. ``make`` alone lists every command.

.. code-block:: console

    $ make test             # the unit tests
    $ make coverage         # with a coverage report: at least 90%
    $ make lint             # the pre-commit hooks, on every file
    $ make sphinx-build     # these docs, with warnings as errors
    $ make build            # the sdist and wheel, checked with twine

Tests
-----

The **unit tests** never reach a platform: an ``httpx`` mock transport answers every request,
with sanitized copies of real platform responses. CI runs them on every supported Python version,
and fails when coverage drops below 90%.

The **live tests** check the SDK against a running platform. They validate every model against
real responses, including a ``describe`` of a real resource of every kind, parsed as its SAM model.
They prompt an LLMClient, which makes billable LLM requests, and they never deploy anything.

.. code-block:: console

    $ SMARTER_BASE_URL=http://localhost:9357 SMARTER_API_KEY=<api key> make test-live

Keeping in step with the platform
---------------------------------

Two things are copied from the platform, and each has a command that refreshes it:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Command
     - What it refreshes
   * - ``make contracts``
     - The platform's :doc:`api contract </smarter-framework/smarter-api/api-contract>`,
       from a checkout of the platform beside the SDK (``../smarter``): the JSON Schema and example
       manifest of every SAM kind, the api's OpenAPI document, and the chat and journal contracts'
       JSON Schemas and examples. ``SMARTER_REF=<ref>`` reads them at a commit or tag, e.g.
       ``origin/main``.
   * - ``make sam-models``
     - ``make contracts``, then the SAM models, generated from the SAM JSON Schemas. No running
       platform is needed.

When the platform changes a contract or a manifest kind, refresh, run the tests, and fix what they
find.

Documentation
-------------

These pages are in the repository's ``docs/source/`` folder, and the
:doc:`API reference <reference>` is autodoc of the SDK's own docstrings: to fix a reference
page, fix the docstring. Every docs change is built in CI with warnings as errors, so run
``make sphinx-build`` before you open a pull request.

Pull requests
-------------

1. Fork the repository, and branch from ``main``.
2. Make your change with its tests. ``make coverage`` must stay at 90% or more, and the live tests
   must pass against a local platform when you change a model or an endpoint.
3. Update the docs and docstrings for anything a user can see.
4. Write `conventional commits <https://www.conventionalcommits.org/>`__, e.g.
   ``fix(llmclients): add verbose option to config()``. Releases are versioned from them: ``fix``
   makes a patch release, ``feat`` a minor one.
5. Open a pull request that says what changed and why, and links its issue.

Code of conduct
---------------

Everyone who takes part is expected to follow the
`code of conduct <https://github.com/smarter-sh/smarter-python/blob/main/CODE_OF_CONDUCT.md>`__.
Governance of the Smarter projects is described in
`smarter-sh/community <https://github.com/smarter-sh/community>`__.
