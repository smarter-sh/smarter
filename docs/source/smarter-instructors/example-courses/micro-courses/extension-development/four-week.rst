Extension Development: Four-Week Online Course
==============================================

A four-week online course on building tools for LLMs as Smarter Extensions: Python packages that a
platform administrator installs at run time, and that every LLMClient on the platform can then
use. Students learn from the official `weather Extension
<https://github.com/smarter-sh/smarter-extension-weather>`__, which implements the ``get_weather``
tool of OpenAI's function calling guide for real, from the open source framework that runs it,
`apps/llmtool/extension/
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmtool/extension>`__, and
from the signed `extensions-registry <https://github.com/smarter-sh/extensions-registry>`__ that
publishes it. There are twelve 30-minute recorded lectures and a 90-minute live session each
week. Week 1 covers tools and the framework, week 2 writing tools, week 3 settings, the lifecycle
and testing, and week 4 loading, publishing and trust. See :doc:`../course-formats` for the
format, the grading scale and the course policies, and :doc:`../extension-development` for an
overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Python developers who want to give LLMs new abilities.
   * - **Deployment**
     - Each student runs Smarter from source (``make init``), as its superuser. Extensions are
       installed by a superuser, so a shared instance doesn't suit this course. Week 1 includes
       time for setup.
   * - **Models**
     - Any OpenAI-compatible model that supports tool calling, through the instructor's provider
       key.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Under $10 per student in model charges, capped with a
       :doc:`Budget </smarter-resources/smarter-budget>`. The weather Extension needs a Google Maps
       Geocoding API key, whose free monthly allowance covers the course. A GitHub account's free
       Actions minutes cover the release workflow.

Learning Objectives
-------------------

By the end of the course, students can:

1. Explain how Smarter offers a tool to an LLM, runs its call and returns the result, and choose
   between a Plugin, an Extension and an MCP server for a given need.
2. Write an Extension's ``pyproject.toml`` and tools whose Pydantic arguments models are their
   definitions.
3. Design tools' results and error messages for an LLM to read, and treat its arguments as
   untrusted input.
4. Use settings, secrets, waffle switches, SAM resources and lifecycle hooks to manage what an
   Extension needs on a platform.
5. Test tools without the platform, the database or an LLM, and run the tests in CI.
6. Package, version, release and publish an Extension, and evaluate the risks of installing
   someone else's.

Technical Prerequisites
-----------------------

- **Required:** Python: classes and inheritance, type hints, exceptions, packages and relative
  imports.
- **Required:** Git, GitHub and pull requests.
- **Required by the end of week 1:** Docker, and Smarter installed from source with a superuser
  login. See the :doc:`Smarter Instructor Guide </smarter-instructor>`.
- **Helpful:** `Pydantic <https://docs.pydantic.dev/>`__ models, Python's ``unittest`` and
  ``unittest.mock``, GitHub Actions, and having called an LLM API.
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
     - Lecture 1
     - **How LLMs call tools.** Tool definitions, tool calls and results, and the loop that runs
       them in ``openai_compatible_chat_provider.py``: ``handle_extensions()`` and
       ``process_tool_call()``. :doc:`/smarter-resources/llmtool/how-tools-work`.
   * - 1
     - Lecture 2
     - **Plugins, Extensions and MCP.** Configuration or code, account or platform, selected by
       search terms or offered on every prompt: :doc:`/smarter-framework/extensibility`. Why
       Extensions replaced three functions hardcoded in the chat provider, read from the body of
       `commit fda234a37
       <https://github.com/smarter-sh/smarter/commit/fda234a37245907c40197a503822c113eb041f0a>`__.
   * - 1
     - Lecture 3
     - **A tour of the weather Extension.** Its ``pyproject.toml``, docstring, models, services
       and tool, and how its result changed in 0.2.0 (`commit 51ec052a5
       <https://github.com/smarter-sh/smarter-extension-weather/commit/51ec052a5ffb8515b0ceff337d744b1ad5cd0e10>`__).
   * - 1
     - Live session 1
     - Setup triage. Enabling the weather Extension in the web console, and tracing a tool call
       live. Start Assignment 1.
   * - 2
     - Lecture 4
     - **The pyproject.toml.** ``[project]`` and ``[tool.smarter]``, validated by
       ``manifest.py``: the permanent slug, ``requires-smarter``, dependencies that are checked
       but never installed, and ``compatibility_problems()``.
       :doc:`/smarter-framework/extensions/pyproject-reference`.
   * - 2
     - Lecture 5
     - **The tool protocol.** ``SmarterExtensionTool`` and ``ExtensionContext`` in
       ``protocol.py``; the docstring as the description and the arguments model as the JSON
       Schema; ``problems()``; and what ``validate_extension`` prints. :doc:`ADR 031
       </adr/031-pydantic-over-json>`.
   * - 2
     - Lecture 6
     - **Results and errors for an LLM.** Results that need no guessing, ``ExtensionToolError``
       messages written for the LLM, and what ``toolkit.py`` does with invalid arguments,
       exceptions, timeouts and non-JSON. The LLM's arguments as untrusted input: the
       calculator's ``evaluator.py``.
   * - 2
     - Live session 2
     - Review of Assignment 1. Designing an arguments model together, and watching the LLM use it.
       Start Assignment 2.
   * - 3
     - Lecture 7
     - **Settings and secrets.** Typed settings and ``SecretStr`` in ``settings.py``, secrets
       stored as Smarter Secrets, and the naming convention that lets ``add_builtin_extensions``
       configure them.
   * - 3
     - Lecture 8
     - **The lifecycle.** Waffle switches and SAM manifests that an Extension creates and its
       uninstall removes (``resources.py``), the eight hooks (``lifecycle.py``), and the
       installer's order of work. :doc:`/smarter-framework/extensions/lifecycle`.
   * - 3
     - Lecture 9
     - **Testing.** ``call_tool()`` and ``tool_context()`` in ``testing.py``; mocking services;
       ``manage.py test_extension``; the framework's own fixtures (``echo``, ``broken``,
       ``incompatible``); and CI that tests against a checkout of Smarter
       (``test.yml`` in the weather repository).
   * - 3
     - Live session 3
     - Review of Assignment 2. A test-writing workshop on the planted bugs of an instructor's
       Extension. Capstone proposals discussed. Start Assignment 3.
   * - 4
     - Lecture 10
     - **Loading code at run time.** ``loader.py``: one archive per version in the database,
       atomic extraction, a module namespace per version and sha256, and why that needs relative
       imports and no work at import time.
   * - 4
     - Lecture 11
     - **Packaging and publishing.** The archive's limits and reproducible builds
       (``archive.py``), semantic-release (`commit 45f3690c2
       <https://github.com/smarter-sh/smarter-extension-weather/commit/45f3690c2ba793306a2e1f467c7217e579e2b7c8>`__),
       and the registry: entries, validation, the signed index and trust badges.
       :doc:`/smarter-framework/extensions/publishing`.
   * - 4
     - Lecture 12
     - **Trust and operations.** Extensions run with the platform's own access, unsandboxed. The
       registry's signature and sha256 checks, and what they do and don't protect. Updates,
       rollbacks and errors on the web console's Extensions pages
       (:doc:`/smarter-platform/extensions`), and the signals that log every tool call.
   * - 4
     - Live session 4
     - Capstone presentations (about 6 minutes each, with 2 minutes of questions), and a course
       retrospective.

Assignments 1 to 3 are due before the next live session. Assignment 4 is due in the middle of week
4. The capstone proposal is due before Live session 3, and the capstone at the start of Live
session 4.

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

Assignment 2: Two Tools
~~~~~~~~~~~~~~~~~~~~~~~

Students write an Extension with two related tools that do something an LLM can't do reliably on
its own, with described Pydantic arguments and result models, and show an LLMClient choosing
between them correctly.

**Turn in:** a Git repository with the Extension, the output of ``validate_extension``, and a
conversation that uses both tools.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Models
     - 6
     - Arguments and results typed, constrained and described.
     - Bare fields and hand-built dicts.
   * - Tool choice
     - 5
     - Descriptions distinct enough that the LLM picks the right tool.
     - The LLM confuses the two.
   * - Untrusted input
     - 5
     - Every argument checked before use; nothing evaluated or executed.
     - Trusts the LLM.
   * - Valid Extension
     - 4
     - ``validate_extension`` passes; relative imports; nothing done at import time.
     - Validates only after help.

Assignment 3: Settings, a Hook and Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students add a secret setting and a waffle switch to their Extension, and a lifecycle hook that
checks something real, such as ``on_enable`` refusing to enable without a working API key. They
test the tools and the hook with every service mocked.

**Turn in:** the updated repository, its ``test_extension`` output, and screenshots of the
settings form and of the hook refusing to enable.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Settings
     - 5
     - Typed, described, and the secret never logged or returned.
     - A secret in a log or a result.
   * - Hook
     - 5
     - A real check, in the right hook, with a clear message.
     - A hook that does nothing useful.
   * - Tests
     - 6
     - Success, invalid arguments, tool errors and the hook, with no network.
     - Only the success.
   * - Verified
     - 4
     - The hook's refusal shown on the platform, not only in a test.
     - Took the test's word for it.

Assignment 4: A Release Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students add CI to their Extension's repository, modeled on the weather Extension's ``test.yml``
and ``release.yml``: tests on every pull request, and a release on each push to ``main`` that
builds the archive and attaches it with its sha256. They write the registry entry that a release
would need, without submitting it.

**Turn in:** the repository with two passing workflow runs and a GitHub release, and the draft
``extensions/<slug>/<version>.yaml``.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Tests in CI
     - 5
     - Run against a checkout of Smarter, on every pull request.
     - Run only locally.
   * - Release
     - 6
     - Versioned from commit types, with the archive and sha256 attached.
     - A hand-made tag.
   * - Reproducible
     - 5
     - Two builds of the same commit have the same sha256, shown.
     - Not checked.
   * - Registry entry
     - 4
     - Slug, version, URL and sha256 all match the release.
     - A sha256 copied from elsewhere.

Capstone Projects
-----------------

Students choose one, propose it before Live session 3, and present it in Live session 4.

Capstone A: A Published Extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build, test, release and publish an Extension that gives an LLM an
ability it lacks, to the standard of the official Extensions.

Students build an Extension around a real service or computation, with at least two tools,
settings including a secret, a SAM resource or waffle switch, and a lifecycle hook. It is tested
in CI, released by its workflow, and documented for administrators. They install it from its
GitHub release on a clean platform, and show LLMClients using it. A capstone that submits its
Extension to the Smarter registry agrees this with the maintainers in an issue on
``extensions-registry`` first, and follows :doc:`/smarter-framework/extensions/publishing`.

**What students turn in:**

- The Extension's repository, with its workflows, releases and ``CHANGELOG.md``.
- A conversation in which an LLMClient uses each tool, including one failure it recovers from.
- A two-page design note on the tools, settings, lifecycle and the trust an administrator must
  place in it.
- A six-minute presentation, with questions on the code.

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
     - The LLM ignores a tool, or guesses at its result.
   * - Robustness
     - 20
     - Input validated as untrusted; every failure returns a useful error; nothing runs at import.
     - Exceptions escape, or the Extension fails to load.
   * - Settings and lifecycle
     - 15
     - Each used for a real need; uninstall leaves nothing behind.
     - Declared but unused, or left behind on uninstall.
   * - Tests and CI
     - 20
     - Mocked, thorough, and passing in CI.
     - Tests need an API key, or CI is red.
   * - Release and documentation
     - 10
     - A reproducible release, installed from GitHub; documentation an administrator can act on.
     - Installed only from a local build.
   * - Presentation
     - 10
     - Clear, and answers questions on any line.
     - Can't explain key parts.

Capstone B: A Security Review of the Extension Framework
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Evaluate the trust model of a plugin system that runs other people's
code, and propose improvements that keep it usable.

Students threat-model the path from a developer's repository to a tool call: the archive, the
registry's CI, the signed index, the download, the installer, the loader, the toolkit and the
settings. For each threat they cite the code that addresses it, or show that nothing does, with a
demonstration Extension installed only on their own platform. They propose two improvements as
Architecture Decision Records, such as sandboxing tool calls or signing archives by publisher.

**What students turn in:**

- A threat model, as a table of assets, threats, existing controls (with file references) and
  gaps.
- The demonstration Extension's repository, and evidence of each demonstration.
- Two draft ADRs in the format of :doc:`/adr`.
- A six-minute presentation.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Coverage
     - 20
     - Every step from repository to tool call.
     - The archive only.
   * - Evidence
     - 25
     - Each control cited in the code; each gap demonstrated.
     - Claims without references.
   * - Demonstrations
     - 15
     - Safe, on the student's own platform, and convincing.
     - Hypothetical.
   * - Proposals
     - 25
     - Two ADRs with alternatives, costs and effect on developers.
     - "Add sandboxing", with no design.
   * - Presentation
     - 15
     - Clear and proportionate.
     - Alarmist or vague.

Recommended Texts
-----------------

- **Required:** :doc:`/smarter-framework/extensibility` and
  :doc:`/smarter-framework/extensions/developer-guide`, in week 1.
- **Required:** OpenAI's `function calling guide
  <https://platform.openai.com/docs/guides/function-calling>`__, in week 1.
- **Required:** :doc:`/smarter-framework/extensions/lifecycle` and
  :doc:`/smarter-framework/extensions/testing`, in week 3.
- **Required:** :doc:`/smarter-framework/extensions/publishing` and
  :doc:`/smarter-platform/extensions`, in week 4.
- **Reference:** Luciano Ramalho, *Fluent Python* (2nd edition, O'Reilly, 2022), on classes,
  type hints and packages.
- **Reference:** Chip Huyen, *AI Engineering* (O'Reilly, 2025), on how tools and agents fit into
  AI applications.
- **Reference:** Harry Percival and Bob Gregory, *Architecture Patterns with Python* (O'Reilly,
  2020), on keeping services apart from the code that calls them, as the weather Extension's
  ``services.py`` does.
- **In the repository:** `protocol.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/extension/protocol.py>`__,
  `toolkit.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/extension/toolkit.py>`__,
  `loader.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/extension/loader.py>`__,
  and the `weather Extension <https://github.com/smarter-sh/smarter-extension-weather>`__.

Further Study
-------------

.. include:: further-study.txt
