Extension Development: Two-Week Online Course
=============================================

A two-week online course on building tools for LLMs as Smarter Extensions: Python packages that a
platform administrator installs at run time, and that every LLMClient on the platform can then
use. Students learn from the official `weather Extension
<https://github.com/smarter-sh/smarter-extension-weather>`__, which implements the ``get_weather``
tool of OpenAI's function calling guide for real, and from the open source framework that runs it,
`apps/llmtool/extension/
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmtool/extension>`__. They
trace a tool call through the platform, write and test an Extension of their own, and package and
install it. There are six 30-minute recorded lectures and a 90-minute live session each week. See
:doc:`../course-formats` for the format, the grading scale and the course policies, and
:doc:`../extension-development` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Python developers who want to give LLMs new abilities.
   * - **Deployment**
     - Each student runs Smarter from source (``make init``), as its superuser. Extensions are
       installed by a superuser, so a shared instance doesn't suit this course.
   * - **Models**
     - Any OpenAI-compatible model that supports tool calling, through the instructor's provider
       key.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Under $5 per student in model charges, capped with a
       :doc:`Budget </smarter-resources/smarter-budget>`. The weather Extension needs a Google Maps
       Geocoding API key, whose free monthly allowance covers the course.

Learning Objectives
-------------------

By the end of the course, students can:

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
- **Required by the end of week 1:** Docker, and Smarter installed from source with a superuser
  login. Install it before the course starts: two weeks leave little time for setup. See the
  :doc:`Smarter Instructor Guide </smarter-instructor>`.
- **Helpful:** `Pydantic <https://docs.pydantic.dev/>`__ models, Python's ``unittest`` and
  ``unittest.mock``, and having called an LLM API.
- **Not needed:** Django or JavaScript. The framework hides both.

Schedule
--------

The files that the lectures refer to are listed in full under `Smarter in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1 (30 min)
     - **Tools and extensibility.** The tool call loop, and where Smarter runs it
       (``handle_extensions()`` and ``process_tool_call()`` in
       ``openai_compatible_chat_provider.py``). Plugins, Extensions and MCP servers compared, with
       :doc:`/smarter-framework/extensibility`, and why Extensions replaced three functions
       hardcoded in the chat provider (`commit fda234a37
       <https://github.com/smarter-sh/smarter/commit/fda234a37245907c40197a503822c113eb041f0a>`__).
   * - 1
     - Lecture 2 (30 min)
     - **Anatomy of an Extension.** The weather Extension's files, its ``pyproject.toml``
       (validated by ``manifest.py``), its docstring as documentation, and relative imports.
       :doc:`/smarter-framework/extensions/pyproject-reference`.
   * - 1
     - Lecture 3 (30 min)
     - **The tool protocol, results and errors.** ``SmarterExtensionTool`` and
       ``ExtensionContext`` in ``protocol.py``; what ``toolkit.py`` does with every kind of
       failure; results that name their units and timezone (`commit 51ec052a5
       <https://github.com/smarter-sh/smarter-extension-weather/commit/51ec052a5ffb8515b0ceff337d744b1ad5cd0e10>`__);
       and the LLM's arguments as untrusted input, in the calculator's ``evaluator.py``.
       The same principles in another protocol: "Tools for an LLM" in the case study `The Smarter
       Project MCP Server <https://smarter.sh/case-studies/mcp-server>`__ ("Errors teach",
       "Arguments can't be wrong"), and "Make a mistake on purpose" in its "Lab 2: Call the
       server".
   * - 1
     - Live session 1 (90 min)
     - Enabling the weather Extension in the web console and tracing a tool call live. Then each
       student starts an Extension of their own, from the date calculator, and runs
       ``validate_extension`` on it. Start Assignments 1 and 2.
   * - 2
     - Lecture 4 (30 min)
     - **Settings, secrets and the lifecycle.** Typed settings and ``SecretStr``
       (``settings.py``), switches and SAM resources (``resources.py``), and the eight lifecycle
       hooks (``lifecycle.py``). :doc:`/smarter-framework/extensions/lifecycle`.
   * - 2
     - Lecture 5 (30 min)
     - **Testing.** ``call_tool()`` and ``tool_context()`` in ``testing.py``, mocking services,
       and ``manage.py test_extension``. :doc:`/smarter-framework/extensions/testing`.
   * - 2
     - Lecture 6 (30 min)
     - **Publishing and trust.** The archive (``archive.py``), loading versions side by side
       (``loader.py``), releasing with semantic-release, the signed registry and its trust
       badges, and why an Extension, which runs with the platform's own access, should come only
       from a publisher you trust. :doc:`/smarter-framework/extensions/publishing`.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: A Tool Call, Traced
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students follow two weather questions, one that succeeds and one that fails, from the prompt to
the answer, naming the code that handles each step, and compare the tool definition that
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
such as a unit conversion, a checksum or a lookup in a bundled table, with a setting an
administrator configures. ``validate_extension`` must pass, and print the definition they
intended.

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

Assignment 3: Tested and Installed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students test their tool with ``call_tool()`` and ``tool_context()``, covering a success, invalid
arguments and an ``ExtensionToolError`` with every network call mocked. They build its archive with
``package_extension``, install and configure it on their platform, and show an LLMClient using it.

**Turn in:** the tests in the Extension's repository, their ``test_extension`` output, the
archive's sha256, and the conversation.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Cases covered
     - 6
     - Success, invalid arguments and a tool error, each asserted precisely.
     - Only the success.
   * - Isolation
     - 4
     - No network, no API keys, no LLM.
     - Calls the real service.
   * - Installed and used
     - 6
     - Installed from its archive, configured, and called by an LLMClient.
     - Shown only in tests.
   * - Runs as shown
     - 4
     - The output and sha256 match the repository.
     - Took the tests' passing on trust; output not included.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

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
- A five-minute presentation.

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
- A five-minute presentation.

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
   * - Presentation
     - 10
     - Concise and organized.
     - Long or disorganized.

Recommended Texts
-----------------

- **Required:** :doc:`/smarter-framework/extensibility`,
  :doc:`/smarter-framework/extensions/developer-guide` and OpenAI's `function calling guide
  <https://platform.openai.com/docs/guides/function-calling>`__, in week 1.
- **Required:** :doc:`/smarter-framework/extensions/testing` and
  :doc:`/smarter-framework/extensions/publishing`, in week 2.
- **Reference:** Luciano Ramalho, *Fluent Python* (2nd edition, O'Reilly, 2022), on classes,
  type hints and packages.
- **Reference:** Chip Huyen, *AI Engineering* (O'Reilly, 2025), on how tools and agents fit into
  AI applications.
- **In the repository:** `protocol.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/extension/protocol.py>`__,
  `toolkit.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/extension/toolkit.py>`__
  and the `weather Extension <https://github.com/smarter-sh/smarter-extension-weather>`__.

Further Study
-------------

.. include:: further-study.txt
