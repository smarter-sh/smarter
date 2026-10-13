Developing the SDK
==================

The SDK's source is `github.com/smarter-sh/smarter-python <https://github.com/smarter-sh/smarter-python>`__.
It follows the platform's practices and :doc:`architecture decisions <../../adr>`: the same
pre-commit hooks, reStructuredText docstrings, semantic versioning and conventional commits. Its
own decisions are recorded in its ``doc/adr/`` folder, and its Agent Skills in ``skills/``
describe how it is developed, for people and for AI coding agents.

.. code-block:: console

   git clone https://github.com/smarter-sh/smarter-python.git
   cd smarter-python
   make init                     # a virtual environment, development requirements and pre-commit
   make test                     # the unit tests
   make coverage                 # with a coverage report

Tests
-----

The **unit tests** never reach a platform: an ``httpx`` mock transport answers every request,
with sanitized copies of real platform responses. They run in CI on every supported Python
version, which also checks that coverage stays at 90% or more.

The **live tests** check the SDK against a running platform. They validate every model against
real responses, including a ``describe`` of a real resource of every kind, parsed as its SAM model.
They prompt an LLMClient, which makes billable LLM requests, and they never deploy anything.

.. code-block:: console

   SMARTER_BASE_URL=http://localhost:9357 SMARTER_API_KEY=<api key> make test-live

Keeping in step with the platform
---------------------------------

Three things are copied from the platform, and each has a command that refreshes it:

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
     - ``make contracts``, then the SAM models, generated from the SAM JSON Schemas. No running
       platform is needed.
   * - ``python scripts/generate_reference.py``
     - The SDK's :doc:`API reference <reference>` pages in the platform's documentation.

When the platform changes a contract or a manifest kind, refresh, run the tests, and fix what they
find.

The SDK's API reference
-----------------------

The platform's documentation autodocs the platform's own ``smarter`` package, and the SDK's import
name is ``smarter`` too, so the documentation build can't import the SDK. Its reference pages are
generated instead, from the SDK's docstrings, as Sphinx directives that need no import. Don't edit
them: change the docstring, and regenerate.
