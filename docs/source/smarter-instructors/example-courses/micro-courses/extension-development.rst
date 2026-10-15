Extension Development
=====================

**Why Smarter.** Courses on tool calling usually stop at a function in a notebook: a
``get_weather`` that returns a hard-coded forecast, called once by a model, with nothing to
install, configure, test, version, publish or trust. Real tools need all of that. Smarter's
:doc:`Extensions </smarter-framework/smarter-extensions>` are Python packages that add tools to
every LLM on a platform, installed by an administrator at run time, much as a WordPress
administrator installs a plugin, and published through a signed public registry. The framework,
its official Extensions and its registry are all open source, so students can read each step that
a tool takes, from the developer's ``pyproject.toml`` to the LLM's tool call:

- **A tool is a class.** Its docstring is the description that the LLM reads, and its Pydantic
  arguments model is the JSON Schema of its parameters, so the definition and the validation can
  never disagree: `protocol.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/extension/protocol.py>`__.
- **Failures are the LLM's to handle.** Invalid arguments, exceptions, timeouts and non-JSON
  results come back to the LLM as errors that it can recover from, instead of failing the prompt:
  `toolkit.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/extension/toolkit.py>`__.
- **A real worked example.** The official `weather Extension
  <https://github.com/smarter-sh/smarter-extension-weather>`__ implements the tool that OpenAI's
  function calling guide describes, with a secret API key, two third-party services and a result
  that names its timezone and units. A `calculator
  <https://github.com/smarter-sh/smarter-extension-calculator>`__ shows how to treat the LLM's
  input as untrusted.
- **Code loaded at run time, safely.** Each version is imported under a name of its own, so an
  update loads beside the old one in every pod, without a redeploy: `loader.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/extension/loader.py>`__.
- **A signed registry.** Releases are pull requests to a public `registry
  <https://github.com/smarter-sh/extensions-registry>`__ whose CI signs an index with Ed25519.
  Platforms verify the signature and every archive's sha256 before they install.
- **Testable without the platform.** ``call_tool()`` and ``tool_context()`` run a tool as the
  platform does, without a database or an LLM: `testing.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmtool/extension/testing.py>`__.

Smarter also keeps the simpler alternative beside it. A
:doc:`Plugin </smarter-resources/smarter-llmtool>` is a YAML manifest that configures one of six
built-in tool patterns, with no code at all, so students learn when *not* to write an Extension.

**What the course covers.** How LLMs call tools, and the three ways to give a Smarter LLMClient
tools: Plugins, Extensions and MCP servers; the anatomy of an Extension and its
``pyproject.toml``; the tool protocol, with Pydantic arguments and results; designing results and
error messages for an LLM to read; settings, secrets, waffle switches, SAM resources and lifecycle
hooks; testing tools without the platform; how the platform loads code at run time; packaging,
versioning and releasing with CI; the signed registry, trust badges and the security of running
other people's code; and operating Extensions in the web console.

**Look at.**

- `smarter/smarter/apps/llmtool/extension/
  <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmtool/extension>`__, the
  Extension framework.
- `smarter-extension-weather <https://github.com/smarter-sh/smarter-extension-weather>`__, the
  developer guide's worked example.
- `extensions-registry <https://github.com/smarter-sh/extensions-registry>`__, the signed
  registry.
- `smarter/smarter/apps/llmtool/plugin/
  <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/llmtool/plugin>`__, the
  Plugin patterns, for comparison.

Each course plan lists every file that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-framework/extensibility`, :doc:`/smarter-framework/smarter-extensions`,
:doc:`/smarter-framework/extensions/developer-guide`, :doc:`/smarter-platform/extensions`,
:doc:`/smarter-resources/llmtool/how-tools-work`.

**Exercises.**

- Run ``manage.py validate_extension`` on the weather Extension and compare the tool definition
  it prints with ``weather/models.py``. Where does each part of the definition come from?
- Ask the weather LLMClient a question that it can't answer, such as the weather in Atlantis, and
  trace the ``ExtensionToolError`` from ``weather/tools.py`` to the LLM's apology.
- Read the calculator's ``evaluator.py``, then try to make it run code or exhaust memory, and
  explain why each attempt fails.
- Implement the same tool twice, as an :doc:`API Plugin </smarter-resources/llmtool/plugin/api>`
  and as an Extension, and compare what each took to write, test and deploy.
- Read the loader, and explain why an Extension's modules must use relative imports.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common. The
:doc:`../master-classes/ai-application-development` goes further, into the chat provider's tool
call loop that runs Extensions' tools.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <extension-development/bootcamp>
   Two-week online course: 6 hours <extension-development/two-week>
   Four-week online course: 12 hours <extension-development/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
