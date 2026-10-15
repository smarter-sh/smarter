Extension Development: Classroom Bootcamp
=========================================

An eight-hour classroom bootcamp on building tools for LLMs as Smarter Extensions: Python
packages that a platform administrator installs at run time, and that every LLMClient on the
platform can then use. Students learn from the official `weather Extension
<https://github.com/smarter-sh/smarter-extension-weather>`__, which implements the ``get_weather``
tool of OpenAI's function calling guide for real, and from the open source framework that runs it,
`apps/llmtool/extension/
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmtool/extension>`__.
During the day they trace a tool call through the platform, write an Extension of their own with a
Pydantic arguments model, test it without the platform, and package and install it. See
:doc:`../course-formats` for the standard bootcamp day, the grading scale and the course policies,
and :doc:`../extension-development` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Python developers who want to give LLMs new abilities.
   * - **Deployment**
     - Each student runs Smarter from source (``make init``), installed and working **before**
       the bootcamp. Extensions are installed by a superuser, so a shared instance doesn't suit
       this course.
   * - **Models**
     - Any OpenAI-compatible model that supports tool calling, through the instructor's provider
       key.
   * - **Cost**
     - Under $5 per student in model charges, capped with a
       :doc:`Budget </smarter-resources/smarter-budget>`. The weather Extension needs a Google Maps
       Geocoding API key, whose free monthly allowance covers the course; the calculator
       Extensions need none.

Learning Objectives
-------------------

By the end of the bootcamp, students can:

1. Explain how Smarter offers a tool to an LLM, runs its call and returns the result, and choose
   between a Plugin, an Extension and an MCP server for a given need.
2. Write an Extension's ``pyproject.toml`` and a tool whose Pydantic arguments model is its
   definition.
3. Design a tool's result and error messages for an LLM to read.
4. Test a tool without the platform, the database or an LLM.
5. Package, install, configure and use an Extension, and explain the risks of installing
   someone else's.

Technical Prerequisites
-----------------------

- **Required:** Python: classes and inheritance, type hints, exceptions, packages and relative
  imports.
- **Required:** Git and a GitHub account.
- **Required:** Docker, and Smarter installed from source, proved working with a screenshot of the
  web console before the bootcamp. See the :doc:`Smarter Instructor Guide </smarter-instructor>`.
- **Required:** a superuser login on that installation, which ``make init`` creates.
- **Helpful:** `Pydantic <https://docs.pydantic.dev/>`__ models, Python's ``unittest`` and
  ``unittest.mock``, and having called an LLM API.
- **Not needed:** Django or JavaScript. The framework hides both.

Schedule
--------

The files that the lectures refer to are listed in full under `Smarter in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 8 8 84

   * - Block
     - Min
     - Content
   * - 1
     - 45
     - **Lecture 1: Tools and extensibility.** The tool call loop, and where Smarter runs it
       (``handle_extensions()`` and ``process_tool_call()`` in
       ``openai_compatible_chat_provider.py``). Three ways to add tools: Plugins, Extensions and
       MCP servers, compared with :doc:`/smarter-framework/extensibility`. Why Extensions
       replaced the three Python functions that were hardcoded in the chat provider
       (`commit fda234a37
       <https://github.com/smarter-sh/smarter/commit/fda234a37245907c40197a503822c113eb041f0a>`__).
   * - 2
     - 45
     - **Lab 1: A tool call, traced.** In the web console's **Extensions** page, configure the
       weather Extension's ``google_maps_api_key`` and enable it. Chat with the built-in
       ``weather`` LLMClient, ask about a real place and an imaginary one, and find each tool call,
       its arguments and its result in the chat's Smarter messages and the logs. Run
       ``manage.py validate_extension`` on a clone of the weather Extension. Produces
       Assignment 1.
   * - 3
     - 45
     - **Lecture 2: Anatomy of an Extension.** The weather Extension's files. The
       ``pyproject.toml``'s ``[project]`` and ``[tool.smarter]`` tables, validated by
       ``manifest.py``: a permanent slug, ``requires-smarter``, dependencies that are checked but
       never installed, and settings. The module docstring as documentation. Relative imports, and
       why. :doc:`/smarter-framework/extensions/pyproject-reference`.
   * - 4
     - 45
     - **Lab 2: A first tool.** Starting from the date calculator, students write an Extension of
       their own, with one tool, a described Pydantic arguments model and a module docstring, and
       run ``validate_extension`` until it prints the definition they intended. Produces
       Assignment 2.
   * - 5
     - 45
     - **Lecture 3: The tool protocol.** ``SmarterExtensionTool`` in ``protocol.py``: the class
       docstring as the description, the arguments model as the JSON Schema, and ``problems()``.
       The ``ExtensionContext``: settings, account, user, LLMClient, logger and switches. The
       toolkit's names (``ext_<slug>_<tool>``), thread and timeout. :doc:`ADR 031
       </adr/031-pydantic-over-json>` on modeling JSON with Pydantic.
   * - 6
     - 45
     - **Lecture 4: Results and errors for an LLM.** A result says everything the LLM needs: the
       weather 0.2.0 commit (`51ec052a5
       <https://github.com/smarter-sh/smarter-extension-weather/commit/51ec052a5ffb8515b0ceff337d744b1ad5cd0e10>`__)
       added timezones and units. ``ExtensionToolError`` messages written for the LLM, and what
       the toolkit does with every other failure. The LLM's arguments as untrusted input: the
       calculator's ``evaluator.py`` and its exponent cap. Testing with ``call_tool()`` and
       ``tool_context()``, and mocking the services. :doc:`/smarter-framework/extensions/testing`.
   * - 7
     - 45
     - **Lab 3: Tests.** Students test their tool with ``call_tool()``: a success, invalid
       arguments, an ``ExtensionToolError``, and any third-party service mocked. They run the tests
       in the container with ``manage.py test_extension``. Produces Assignment 3.
   * - 8
     - 45
     - **Lecture 5: Settings, secrets and the lifecycle.** Typed settings and ``SecretStr`` in
       ``settings.py``; waffle switches and SAM manifests that an Extension creates and its
       uninstall removes (``resources.py``); the eight lifecycle hooks and what happens when one
       raises (``lifecycle.py``); the installer as the one place where state changes.
       :doc:`/smarter-framework/extensions/lifecycle`.
   * - 9
     - 45
     - **Lab 4: Ship it to yourself.** Students add a setting to their Extension, build its archive
       with ``package_extension``, install it with ``install_extension``, configure and enable it
       in the web console, list it in an LLMClient's ``spec.extensions``, and chat with it.
       Ungraded.
   * - 10
     - 45
     - **Lecture 6: Publishing and trust.** The archive's limits and reproducible builds
       (``archive.py``); loading versions side by side (``loader.py``); releasing with
       semantic-release; the signed registry, its trust badges, and why an Extension, which runs
       with the platform's own access, should be installed only from a publisher you trust.
       :doc:`/smarter-framework/extensions/publishing`.
   * - 11
     - 30
     - **Capstone kickoff.** Students choose a capstone, and write down the tool or the
       comparison they will build, with its arguments and its result.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: A Tool Call, Traced
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students follow two weather questions, one that succeeds and one that fails, from the prompt to
the answer, naming the code that handles each step. They compare the tool definition that
``validate_extension`` prints with the source that produced it.

**Turn in:** a two-page Markdown report with the conversation, the tool calls, their arguments
and results, and the code that handled each step.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Evidence
     - 6
     - Real tool calls, arguments and results, from the chat and the logs.
     - Paraphrased, or from the docs.
   * - Code located
     - 6
     - Each step tied to the file and method that handles it.
     - Steps named, not located.
   * - Definition explained
     - 5
     - Each part of the definition traced to the docstring, model or slug.
     - Pasted without comment.
   * - Failure path
     - 3
     - Explains how the error reached the LLM, and what it did with it.
     - Only the success.

Assignment 2: A First Tool
~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write an Extension with one tool that does something an LLM can't do reliably on its own,
such as a unit conversion, a checksum or a lookup in a bundled table. ``validate_extension`` must
pass, and print the definition they intended.

**Turn in:** a Git repository with the Extension, and the output of ``validate_extension``.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Valid Extension
     - 5
     - ``validate_extension`` passes; relative imports; nothing done at import time.
     - Validates only after the instructor's help.
   * - Arguments model
     - 6
     - Every field typed, constrained and described for the LLM.
     - Bare ``str`` fields with no descriptions.
   * - Description and docs
     - 5
     - The docstring says what the tool does and when to use it; the module docstring serves an
       administrator.
     - "Does the thing."
   * - Worth a tool
     - 4
     - Does something the LLM gets wrong without it.
     - Something the LLM does well already.

Assignment 3: Tests
~~~~~~~~~~~~~~~~~~~

Students write ``unittest`` tests for their tool with ``call_tool()`` and ``tool_context()``,
covering a success, invalid arguments and an ``ExtensionToolError``, with every network call
mocked, and run them with ``manage.py test_extension``.

**Turn in:** the tests in the Extension's repository, and their output from ``test_extension``.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Cases covered
     - 7
     - Success, invalid arguments and a tool error, each asserted precisely.
     - Only the success.
   * - Isolation
     - 5
     - No network, no API keys, no LLM.
     - Calls the real service.
   * - Errors for the LLM
     - 4
     - Tests check that error messages say what the LLM should do next.
     - Asserts only that an error happened.
   * - Runs as shown
     - 4
     - Output from ``test_extension`` matches the repository.
     - Took the tests' passing on trust; output not included.

Capstone Projects
-----------------

Students choose one. Capstones are due one week after the bootcamp.

Capstone A: An Extension for a Real Need
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build, test and ship an Extension that gives an LLM an ability it lacks,
with settings an administrator configures.

Students build an Extension around a real service or computation, such as a public transit API,
a currency converter with a configurable source, or a domain calculator for their own field. It
has at least two tools or one tool and a secret setting, a result the LLM can interpret without
guessing, tests with every service mocked, and a module docstring for administrators. They install
its archive on their platform and show an LLMClient using it.

**What students turn in:**

- The Extension's Git repository, with tests and a ``README.md``.
- The archive and its sha256, from ``package_extension``.
- A conversation in which an LLMClient uses each tool, including one failure it recovers from.
- A one-page design note on the tools' arguments, results and errors.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Tool design
     - 25
     - Arguments and results modeled and described; the LLM calls each tool when it should.
     - The LLM ignores the tool, or guesses at its result.
   * - Errors and input
     - 20
     - The LLM's input is validated as untrusted, and every failure returns a useful error.
     - Exceptions escape, or messages say only "error".
   * - Tests
     - 20
     - Success and failure paths, with no network.
     - Tests that need an API key.
   * - Settings and docs
     - 15
     - Typed settings, a secret never logged, documentation an administrator can act on.
     - A key in the code, or no documentation.
   * - Working install
     - 20
     - Installed from its archive; the conversation shows every tool working.
     - Shown only in tests.

Capstone B: Plugin or Extension?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Decide, with evidence, when a tool should be configuration and when it
should be code.

Students choose an integration with a public REST API, such as a weather, books or public data
service, and build it twice: as an :doc:`API Plugin </smarter-resources/llmtool/plugin/api>`
with a Connection, and as an Extension. They run the same ten prompts against an LLMClient with
each, and compare the two on effort, behavior, error handling, security and who can maintain them.

**What students turn in:**

- The Plugin manifests and the Extension's repository.
- A table of the ten prompts, with each version's tool calls, answers and tokens.
- A three-page recommendation, citing ``llmtool/plugin/api.py`` and the Extension framework,
  with the cases where each choice is right.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Both versions work
     - 20
     - The same integration, working both ways.
     - One version is a stub.
   * - Fair experiment
     - 25
     - Same prompts, model and LLMClient settings, with results recorded as they came.
     - Different prompts, or results from memory.
   * - Analysis
     - 30
     - Effort, errors, selection, security and maintenance, each with evidence from the code.
     - Opinions without evidence.
   * - Recommendation
     - 15
     - Clear rules for choosing, with their exceptions.
     - "It depends."
   * - Writing
     - 10
     - Concise and organized.
     - Long or disorganized.

Recommended Texts
-----------------

- **Pre-reading:** :doc:`/smarter-framework/extensibility` and OpenAI's `function calling guide
  <https://platform.openai.com/docs/guides/function-calling>`__.
- **Reference:** Luciano Ramalho, *Fluent Python* (2nd edition, O'Reilly, 2022), on classes,
  type hints and packages.
- **Reference:** Chip Huyen, *AI Engineering* (O'Reilly, 2025), on how tools and agents fit into
  AI applications.
- **In the repository:** :doc:`/smarter-framework/extensions/developer-guide`, `protocol.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/extension/protocol.py>`__
  and the `weather Extension <https://github.com/smarter-sh/smarter-extension-weather>`__.

Further Study
-------------

.. include:: further-study.txt
