.. _getting-started-napl-programmers:

.. highlight:: yaml

Getting Started: Claude Code with Smarter at NAPL
==================================================

.. meta::
   :description: Self-onboarding guide for NAPL programmers using Claude Code
                 with the Smarter platform as a virtual CoPilot coding pair.
   :keywords: claude code, smarter, anthropic, napl, copilot, chatbot, yaml

.. contents:: Table of Contents
   :depth: 2
   :local:
   :backlinks: none

----

.. _overview-video:

Platform Overview
-----------------

The following video shows the Smarter chat interface that your deployed
Chatbot agents will present to users in the web console.

.. raw:: html

   <video
     controls
     width="100%"
     style="max-width: 860px; border-radius: 6px; margin: 1em 0;"
     preload="metadata">
     <source src="https://cdn.smarter.sh/videos/read-the-docs2.mp4" type="video/mp4">
     Your browser does not support the HTML5 video element.
     Download the video at
     <a href="https://cdn.smarter.sh/videos/read-the-docs2.mp4">this link</a>.
   </video>

----

Quick Jump
----------

Already onboarded? Jump straight to what you need. New here? Start at
:ref:`goal` and read straight through.

.. list-table::
   :header-rows: 1
   :widths: 20 35 45

   * - Section
     - Link
     - Use this when…
   * - 🎯 Goal
     - :ref:`goal`
     - You want to understand what this tutorial achieves
   * - ✅ Prerequisites
     - :ref:`prerequisites`
     - You want to check what you need before starting
   * - ⚙️ Setup
     - :ref:`setup`
     - You are installing Claude Code for the first time
   * - 💡 Concept Overview
     - :ref:`concept-overview`
     - You want to understand how the pieces fit together
   * - 🪜 Step-by-Step
     - :ref:`step-by-step`
     - You are ready to create and deploy your agents
   * - 🧪 Proof of Concept
     - :ref:`proof-of-concept`
     - You want to verify everything is working
   * - 🔧 Troubleshooting
     - :ref:`troubleshooting`
     - Something is not working
   * - 💻 IDE Integration
     - :ref:`ide-switching`
     - Switching agents in VS Code or JetBrains
   * - 🤝 Pair Programmer
     - :ref:`agent-copilot`
     - General feature development and refactoring
   * - 🔍 Code Reviewer
     - :ref:`agent-reviewer`
     - Pre-commit review and standards enforcement
   * - 🧪 Test Writer
     - :ref:`agent-tester`
     - Writing pytest suites and fixtures
   * - 🐛 Debugger
     - :ref:`agent-debugger`
     - Stack traces and root cause analysis
   * - 📝 Doc Writer
     - :ref:`agent-docwriter`
     - Docstrings, RST pages, CHANGELOG entries
   * - 🛠️ Custom Agents
     - :ref:`custom-agents`
     - Creating your own role-specific agents

----

.. _goal:

Goal
----

We will use **Claude Code** with the **Smarter** platform to create a
virtual CoPilot coding pair — an AI assistant that lives in your terminal,
reads your project files, writes and edits code, and reasons across your
entire codebase, all backed by Anthropic's Claude and managed through
NAPL's on-premise Smarter instance.

By the end of this tutorial you will have:

* Created one or more Smarter Chatbot manifests configured to use
  Anthropic's Claude as their LLM provider.
* Deployed those Chatbots to the Smarter platform using the CLI.
* Installed Claude Code and pointed it at your Smarter Chatbot endpoint.
* Set up a shell-based agent switcher so you can move between specialised
  coding roles — pair programmer, reviewer, tester, debugger, and doc
  writer — with a single command.
* Verified the full pipeline with a working proof-of-concept coding task.

----

.. _why-this-approach:

Why This Approach
-----------------

Using Claude Code through Smarter rather than a standalone AI tool or a
public API account gives the NAPL programming team several concrete
advantages.

**One credential, zero key management**
   You authenticate with your Smarter API key. There is no personal
   Anthropic account to create, no credit card to register, no API key
   to rotate. When you leave a project or the organisation, access is
   revoked in one place.

**Specialised agents instead of a generic chatbot**
   Each YAML manifest defines a focused role — pair programmer, reviewer,
   tester, debugger, or doc writer — with a system prompt tuned for that
   task. You get consistent, on-topic responses without having to
   re-explain your context at the start of every session.

**Your code stays inside NAPL**
   All traffic routes through the on-premise Smarter gateway. Proprietary
   source code, database schemas, and business logic never leave the NAPL
   network boundary to reach a public API endpoint directly.

**Shared standards, enforced automatically**
   The ``defaultSystemRole`` in each manifest encodes NAPL's coding
   conventions — PEP 8, NumPy docstrings, ORM-only database access,
   frozen legacy files. Every developer on the team works with the same
   rules baked in, without relying on individual discipline or
   copy-pasted prompt templates.

**Cost visibility and governance**
   Token consumption is attributed to your team's cost code through
   Smarter's built-in accounting features. The organisation can see
   exactly what AI usage costs, by team and by project, without depending
   on individual developers self-reporting their API spend.

**Version-controlled agent configuration**
   Because each agent is a plain YAML file, the agent definitions live in
   source control alongside your code. Agents can be reviewed, approved,
   and rolled back exactly like any other configuration change. A new
   team member can ``git clone`` the agents repository and have every
   preset available immediately.

**IDE-agnostic**
   Claude Code runs in your terminal. It works the same way regardless of
   whether you use VS Code, a JetBrains IDE, or a plain text editor.
   There is nothing to install in your IDE and no plugin to keep updated.

----

.. _prerequisites:

Prerequisites
-------------

You already have a Smarter account and know how to log in. You are also
expected to be comfortable with:

* **Terminal usage** — environment variables, shell profiles
  (``~/.bashrc`` / ``~/.zshrc``), and basic ``curl``.
* **YAML** — indentation, key/value pairs, and string quoting.
* **Node.js 18+** and **npm** — for installing Claude Code.
* **The Smarter CLI** — ``smarter configure`` and ``smarter apply``.
  If you have not yet configured the CLI, run ``smarter configure``
  and enter your API key and account number from your welcome e-mail.

.. note::

   You do **not** need a personal Anthropic account. NAPL's Smarter
   instance holds the Anthropic API key centrally. Your Smarter API key
   is the only credential you need.

----

.. _setup:

Setup
-----

Install Claude Code
~~~~~~~~~~~~~~~~~~~~

Claude Code is distributed as an npm package::

   npm install -g @anthropic-ai/claude-code

Verify the installation::

   claude --version

Confirm your Smarter CLI is configured
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

   smarter whoami

This should return your username and account number. If it fails, run
``smarter configure`` and re-enter your credentials.

----

.. _concept-overview:

Concept Overview
----------------

How Smarter Manages LLM Providers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Smarter is a **provider-agnostic** platform. The LLM that backs any given
Chatbot is determined by two fields in its YAML manifest: ``provider`` and
``defaultModel``. Anthropic is a supported legacy provider alongside
OpenAI, GoogleAI, MetaAI, and DeepSeek. Changing these two values is all
that is required to move from OpenAI to Claude:

.. code-block:: yaml

   provider: anthropic                   # was "openai"
   defaultModel: claude-sonnet-4-5-20250929  # was "gpt-4-turbo"

Everything else — plugins, system role, UI configuration, token limits —
is identical regardless of which provider backs the Chatbot.

The Smarter Chatbot Manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A Smarter manifest is a YAML file that describes a resource. You apply
it with ``smarter apply -f <file>`` and Smarter creates or updates the
resource to match. The manifest structure follows the same
``apiVersion / kind / metadata / spec`` pattern used throughout the
platform — familiar if you have worked with Kubernetes.

How Claude Code Connects to Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Claude Code is a terminal-based coding agent that speaks the Anthropic
Messages API format. By default it calls Anthropic's public endpoint
directly. Two environment variables redirect it to your Smarter Chatbot
endpoint instead:

.. code-block:: text

   Claude Code (your terminal)
        │
        │  ANTHROPIC_BASE_URL  = your Smarter Chatbot URL
        │  ANTHROPIC_AUTH_TOKEN = your Smarter API key
        ▼
   Smarter Platform  ──►  Anthropic API  ──►  Claude

All traffic is authenticated and logged through Smarter. No direct
Anthropic access from your workstation is required.

What Claude Code Actually Does
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Claude Code is not a chatbot you paste code into. It is an **agentic
coding tool** that runs in your terminal with direct access to your local
filesystem. It can read any file in your project directory, write and
edit files showing you a diff before applying changes, execute shell
commands with your approval, and reason across multiple files
simultaneously to understand architecture, trace bugs, or plan
refactors. Think of it as a senior pair-programming partner who has
already read your entire codebase.

The Role of ``CLAUDE.md``
~~~~~~~~~~~~~~~~~~~~~~~~~~

``CLAUDE.md`` is a Markdown file at the root of your project that Claude
Code reads automatically at the start of every session. It is persistent,
project-specific context — your coding standards, stack description,
prohibited patterns, and common commands. The richer it is, the less you
have to repeat yourself across sessions. The ``/init`` command scans your
project and generates a starter ``CLAUDE.md`` automatically.

----

.. _step-by-step:

Step-by-Step
------------

Step 1 — Create your agent manifest files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each YAML file defines one specialised agent. Create a directory to keep
them organised::

   mkdir ~/napl-agents && cd ~/napl-agents

The two fields that differ between agents are ``metadata.name``,
``spec.config.provider``, ``spec.config.defaultModel``, and most
importantly ``spec.config.defaultSystemRole``. Everything else in the
manifest structure is identical across all agents.

Five ready-to-use presets are provided below. Copy, customise, and
extend them freely.

.. _agent-copilot:

**Pair Programmer** — ``napl-copilot.yaml``

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Chatbot
   metadata:
     description: General-purpose Claude coding assistant for NAPL programmers.
     name: napl-copilot
     version: 1.0.0
     annotations: []
     tags: []
   spec:
     apiKey: null
     config:
       appName: NAPL CoPilot
       appAssistant: CoPilot
       appWelcomeMessage: Hello! I am your NAPL coding assistant. What are we working on?
       appPlaceholder: Describe what you need...
       appExamplePrompts:
         - Add input validation to this function
         - Write pytest tests for this module
         - Explain what this code does
       appInfoUrl: https://napl.internal
       appLogoUrl: https://cdn.smarter.sh/images/logo/smarter-crop.png
       appFileAttachment: false
       appBackgroundImageUrl: null
       customDomain: null
       subdomain: null
       provider: anthropic
       defaultModel: claude-sonnet-4-5-20250929
       defaultSystemRole: >
         You are a senior software engineer and pair-programming assistant
         at Northern Aurora Power & Light. You write clean, well-documented
         code and follow the project's existing conventions. When uncertain,
         ask a clarifying question rather than guessing.
       defaultTemperature: 0.2
       defaultMaxTokens: 4096
       deployed: false
     functions: []
     plugins: []

.. _agent-reviewer:

**Code Reviewer** — ``napl-reviewer.yaml``

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Chatbot
   metadata:
     description: Strict code reviewer focused on quality, security, and standards.
     name: napl-reviewer
     version: 1.0.0
     annotations: []
     tags: []
   spec:
     apiKey: null
     config:
       appName: NAPL Code Reviewer
       appAssistant: Reviewer
       appWelcomeMessage: Ready to review. Paste your code or reference a file.
       appPlaceholder: What should I review?
       appExamplePrompts:
         - Review this function for edge cases
         - Check this module for security issues
         - Does this follow PEP 8 and our naming conventions?
       appInfoUrl: https://napl.internal
       appLogoUrl: https://cdn.smarter.sh/images/logo/smarter-crop.png
       appFileAttachment: false
       appBackgroundImageUrl: null
       customDomain: null
       subdomain: null
       provider: anthropic
       defaultModel: claude-sonnet-4-5-20250929
       defaultSystemRole: >
         You are a strict but constructive code reviewer at Northern Aurora
         Power & Light. You review code for correctness, security
         vulnerabilities, performance issues, and adherence to PEP 8 and
         NumPy-style docstrings. For every issue you find, explain why it
         matters and provide a concrete fix. Do not approve code that has
         unhandled exceptions, missing type hints, or SQL outside the ORM.
       defaultTemperature: 0.1
       defaultMaxTokens: 4096
       deployed: false
     functions: []
     plugins: []

.. _agent-tester:

**Test Writer** — ``napl-tester.yaml``

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Chatbot
   metadata:
     description: Specialist agent for writing pytest test suites.
     name: napl-tester
     version: 1.0.0
     annotations: []
     tags: []
   spec:
     apiKey: null
     config:
       appName: NAPL Test Writer
       appAssistant: Tester
       appWelcomeMessage: Let us write some tests. Show me the code you want covered.
       appPlaceholder: Which module or function needs tests?
       appExamplePrompts:
         - Write full pytest coverage for this service module
         - Add edge case tests for the date validation logic
         - Generate fixtures for the patient model
       appInfoUrl: https://napl.internal
       appLogoUrl: https://cdn.smarter.sh/images/logo/smarter-crop.png
       appFileAttachment: false
       appBackgroundImageUrl: null
       customDomain: null
       subdomain: null
       provider: anthropic
       defaultModel: claude-sonnet-4-5-20250929
       defaultSystemRole: >
         You are a test engineering specialist at Northern Aurora Power &
         Light. Your sole focus is writing comprehensive pytest test suites.
         You always cover the happy path, boundary conditions, and error
         cases. You use fixtures and parametrize where appropriate. You
         never modify source code — only test files. Every test must have
         a clear docstring explaining what it verifies.
       defaultTemperature: 0.1
       defaultMaxTokens: 4096
       deployed: false
     functions: []
     plugins: []

.. _agent-debugger:

**Debugger** — ``napl-debugger.yaml``

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Chatbot
   metadata:
     description: Systematic debugger that traces root causes and explains fixes.
     name: napl-debugger
     version: 1.0.0
     annotations: []
     tags: []
   spec:
     apiKey: null
     config:
       appName: NAPL Debugger
       appAssistant: Debugger
       appWelcomeMessage: >
         Show me the error, the stack trace, and the relevant code.
         I will find the root cause.
       appPlaceholder: Paste your error or describe the unexpected behaviour...
       appExamplePrompts:
         - Here is a stack trace from our Django view — what is wrong?
         - This function returns None instead of a Patient object
         - The Oracle stored procedure raises ORA-01400 intermittently
       appInfoUrl: https://napl.internal
       appLogoUrl: https://cdn.smarter.sh/images/logo/smarter-crop.png
       appFileAttachment: false
       appBackgroundImageUrl: null
       customDomain: null
       subdomain: null
       provider: anthropic
       defaultModel: claude-sonnet-4-5-20250929
       defaultSystemRole: >
         You are a systematic debugging specialist at Northern Aurora Power
         & Light. When presented with a bug, error, or unexpected behaviour
         you follow a structured process: first reproduce the problem in
         your mind by reading the code and stack trace carefully; then
         identify the root cause — not just the symptom; then propose the
         minimal fix with a clear explanation of why the fix works. You
         always distinguish between the immediate error and any underlying
         design issue that should be addressed separately. You never
         guess — if you need more context, ask for it before proposing
         a solution.
       defaultTemperature: 0.1
       defaultMaxTokens: 4096
       deployed: false
     functions: []
     plugins: []

.. _agent-docwriter:

**Documentation Writer** — ``napl-docwriter.yaml``

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Chatbot
   metadata:
     description: Agent specialised in writing NumPy-style docstrings and RST docs.
     name: napl-docwriter
     version: 1.0.0
     annotations: []
     tags: []
   spec:
     apiKey: null
     config:
       appName: NAPL Doc Writer
       appAssistant: DocWriter
       appWelcomeMessage: Ready to document. Show me what needs writing.
       appPlaceholder: What should I document?
       appExamplePrompts:
         - Write NumPy docstrings for all public methods in this file
         - Generate an RST module reference page for this class
         - Write a CHANGELOG entry for these changes
       appInfoUrl: https://napl.internal
       appLogoUrl: https://cdn.smarter.sh/images/logo/smarter-crop.png
       appFileAttachment: false
       appBackgroundImageUrl: null
       customDomain: null
       subdomain: null
       provider: anthropic
       defaultModel: claude-sonnet-4-5-20250929
       defaultSystemRole: >
         You are a technical writer at Northern Aurora Power & Light.
         You write clear, accurate NumPy-style docstrings for Python code
         and Sphinx RST documentation pages. You never change source logic
         — only add or improve documentation. Every docstring must include
         Parameters, Returns, Raises (where applicable), and at least one
         Example.
       defaultTemperature: 0.3
       defaultMaxTokens: 4096
       deployed: false
     functions: []
     plugins: []

Step 2 — Apply all manifests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Register each agent with the Smarter platform::

   smarter apply -f napl-copilot.yaml
   smarter apply -f napl-reviewer.yaml
   smarter apply -f napl-tester.yaml
   smarter apply -f napl-debugger.yaml
   smarter apply -f napl-docwriter.yaml

Verify they were all created::

   smarter get chatbot -o yaml

Step 3 — Deploy the Chatbots
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

   smarter deploy chatbot napl-copilot
   smarter deploy chatbot napl-reviewer
   smarter deploy chatbot napl-tester
   smarter deploy chatbot napl-debugger
   smarter deploy chatbot napl-docwriter

After deployment, retrieve each Chatbot's endpoint URL::

   smarter describe chatbot napl-copilot -o yaml

Note the URL under ``status`` for each agent — they follow the pattern::

   https://napl-copilot.YOUR-ACCOUNT-NUMBER.smarter.napl.internal/chatbot/
   https://napl-reviewer.YOUR-ACCOUNT-NUMBER.smarter.napl.internal/chatbot/
   https://napl-tester.YOUR-ACCOUNT-NUMBER.smarter.napl.internal/chatbot/
   https://napl-debugger.YOUR-ACCOUNT-NUMBER.smarter.napl.internal/chatbot/
   https://napl-docwriter.YOUR-ACCOUNT-NUMBER.smarter.napl.internal/chatbot/

Step 4 — Configure Claude Code and set up the agent switcher
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the following to your shell profile (``~/.bashrc``, ``~/.zshrc``, or
PowerShell ``$PROFILE``):

.. code-block:: bash

   # ── NAPL Smarter credentials ─────────────────────────────────────────
   export ANTHROPIC_AUTH_TOKEN="YOUR_SMARTER_API_KEY"
   export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

   # ── NAPL agent switcher ───────────────────────────────────────────────
   SMARTER_BASE="https://YOUR-ACCOUNT-NUMBER.smarter.napl.internal"

   copilot() {
       export ANTHROPIC_BASE_URL="${SMARTER_BASE}/napl-copilot"
       echo "Agent: napl-copilot (pair programmer)"
       claude "$@"
   }

   reviewer() {
       export ANTHROPIC_BASE_URL="${SMARTER_BASE}/napl-reviewer"
       echo "Agent: napl-reviewer (code reviewer)"
       claude "$@"
   }

   tester() {
       export ANTHROPIC_BASE_URL="${SMARTER_BASE}/napl-tester"
       echo "Agent: napl-tester (test writer)"
       claude "$@"
   }

   debugger() {
       export ANTHROPIC_BASE_URL="${SMARTER_BASE}/napl-debugger"
       echo "Agent: napl-debugger (root cause analysis)"
       claude "$@"
   }

   docwriter() {
       export ANTHROPIC_BASE_URL="${SMARTER_BASE}/napl-docwriter"
       echo "Agent: napl-docwriter (documentation)"
       claude "$@"
   }

Reload your shell::

   source ~/.bashrc

.. important::

   Use ``ANTHROPIC_AUTH_TOKEN``, not ``ANTHROPIC_API_KEY``. Smarter
   authenticates via the ``Authorization: Bearer`` header. If
   ``ANTHROPIC_API_KEY`` is also set, unset it — it will take precedence
   and bypass the gateway::

      unset ANTHROPIC_API_KEY

You can now launch any agent by name from any project directory:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Command
     - Agent role
     - Best used for
   * - ``copilot``
     - Pair programmer
     - Feature development, refactoring, explaining code
   * - ``reviewer``
     - Code reviewer
     - Pre-commit review, security checks, standards enforcement
   * - ``tester``
     - Test writer
     - Writing pytest suites, fixtures, parametrized cases
   * - ``debugger``
     - Debugger
     - Stack traces, unexpected behaviour, root cause analysis
   * - ``docwriter``
     - Documentation writer
     - Docstrings, RST pages, CHANGELOG entries

Step 5 — Initialise Claude Code in a project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Navigate to any project repository and start Claude Code with your
chosen agent::

   cd ~/projects/my-service
   copilot

On your first session in a new project, run ``/init``. Claude Code will
scan your directory, identify the stack and key files, and generate a
``CLAUDE.md`` file at the project root. Open it and add your team's
specific context:

.. code-block:: markdown

   ## Stack
   - Python 3.11, Django 4.2, Oracle 19c
   - Tests: pytest  |  Linter: flake8

   ## Standards
   - PEP 8, type hints on all public functions
   - Docstrings: NumPy style

   ## Do Not Modify
   - legacy/axiUm_bridge.py — open a ticket instead

Commit ``CLAUDE.md`` to source control so all teammates benefit.

Step 6 — Start coding with your agents
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

At the Claude Code prompt, give a concrete, well-scoped task. Reference
files with the ``@`` prefix so Claude knows exactly which context is
relevant::

   Add input validation to the create_patient() function in
   @src/patients/service.py. Raise ValueError if 'date_of_birth'
   is in the future. Add pytest tests in @tests/test_patients.py
   covering the happy path and the error case.

Claude Code reads the files, shows you a diff, waits for your approval,
then applies the changes. Follow up naturally::

   Run the new tests and fix any failures.

For multi-file changes or architectural work, use Plan Mode first::

   /plan
   Refactor the appointment scheduling module to use the repository
   pattern. Identify every file that needs to change before touching
   anything.

----

.. _proof-of-concept:

Proof of Concept
----------------

From a temporary directory, confirm the full pipeline end-to-end::

   mkdir /tmp/napl-poc && cd /tmp/napl-poc
   copilot

At the Claude Code prompt, enter:

.. code-block:: text

   Create a Python file called calculator.py with four functions:
   add, subtract, multiply, and divide. divide should raise
   ZeroDivisionError when the divisor is zero. Then create
   test_calculator.py with full pytest coverage for all four
   functions including the error case. Finally, run the tests
   and confirm they pass.

**Expected outcome** — Claude Code creates both files, runs
``pytest test_calculator.py -v``, and reports::

   PASSED test_calculator.py::test_add
   PASSED test_calculator.py::test_subtract
   PASSED test_calculator.py::test_multiply
   PASSED test_calculator.py::test_divide
   PASSED test_calculator.py::test_divide_by_zero

   5 passed in 0.12s

Five passing tests confirms the complete chain is working:
**your terminal → Smarter → Anthropic → Claude → back**.

----

.. _troubleshooting:

Troubleshooting
---------------

**``smarter apply`` fails with a provider error**

   Confirm the ``provider: anthropic`` field is spelled exactly as shown
   — it is case-sensitive. Also verify your Smarter account has the
   Anthropic provider enabled. Contact NAPL IT if the provider is not
   available in your account.

**Claude Code hangs or returns** ``Unable to connect to API``

   The gateway URL in ``ANTHROPIC_BASE_URL`` is unreachable. Verify::

      curl -I $ANTHROPIC_BASE_URL

   A ``200`` or ``401`` response means the host is up. A timeout means a
   network or VPN issue — connect to the NAPL VPN and retry.

**``401 Unauthorized`` on every request**

   Your ``ANTHROPIC_AUTH_TOKEN`` is missing or incorrect. Check::

      echo $ANTHROPIC_AUTH_TOKEN

   If empty, your shell profile was not reloaded. Run ``source ~/.bashrc``
   or open a new terminal. If the token looks correct but still fails,
   regenerate your Smarter API key via ``smarter configure``.

**``command not found: claude`` after installation**

   The npm global bin directory is not on your ``PATH``. Find it::

      npm config get prefix

   Add the ``bin`` subdirectory of that path to ``PATH`` in your shell
   profile, then reload.

**Claude Code requests approval for every command**

   Use ``/permissions`` to allowlist trusted commands::

      /permissions allow pytest
      /permissions allow flake8
      /permissions allow git

**Context fills up on long sessions**

   Run ``/compact`` to summarise the conversation history without losing
   the thread of what you were working on.

**Changes look wrong after Claude Code edits**

   All changes are shown as diffs before being applied. Type ``n`` at the
   approval prompt to reject any change. If you already accepted something
   unwanted, restore with ``git checkout -- <file>``. Always work on a
   feature branch.

----

.. _ide-switching:

Using and Switching Agents in Your IDE
---------------------------------------

Claude Code runs in a terminal but integrates directly into VS Code and
JetBrains IDEs. The agent in use is determined by the value of
``ANTHROPIC_BASE_URL`` at the moment Claude Code starts — so switching
agents means calling a different switcher function before launching a
new session.

VS Code
~~~~~~~~

**Option 1 — Integrated terminal (recommended)**

Open the integrated terminal (``Ctrl+`` ` `` on Windows/Linux,
``Cmd+`` ` `` on macOS) and call your switcher function directly::

   copilot       # starts the pair programmer
   reviewer      # starts the code reviewer

**Option 2 — VS Code Tasks**

Define a task per agent in ``.vscode/tasks.json`` so you can launch any
agent from the Command Palette (``Ctrl+Shift+P`` → *Run Task*) without
typing in the terminal:

.. code-block:: json

   {
     "version": "2.0.0",
     "tasks": [
       {
         "label": "NAPL: Pair Programmer",
         "type": "shell",
         "command": "copilot",
         "presentation": { "panel": "dedicated", "reveal": "always" },
         "problemMatcher": []
       },
       {
         "label": "NAPL: Code Reviewer",
         "type": "shell",
         "command": "reviewer",
         "presentation": { "panel": "dedicated", "reveal": "always" },
         "problemMatcher": []
       },
       {
         "label": "NAPL: Test Writer",
         "type": "shell",
         "command": "tester",
         "presentation": { "panel": "dedicated", "reveal": "always" },
         "problemMatcher": []
       },
       {
         "label": "NAPL: Debugger",
         "type": "shell",
         "command": "debugger",
         "presentation": { "panel": "dedicated", "reveal": "always" },
         "problemMatcher": []
       },
       {
         "label": "NAPL: Doc Writer",
         "type": "shell",
         "command": "docwriter",
         "presentation": { "panel": "dedicated", "reveal": "always" },
         "problemMatcher": []
       }
     ]
   }

Commit ``.vscode/tasks.json`` to your repository so every team member
gets the same agent launcher menu automatically on ``git pull``.

**Option 3 — Claude Code VS Code extension**

If you have the Claude Code VS Code extension installed, set the agent
in the integrated terminal before opening a session::

   export ANTHROPIC_BASE_URL="${SMARTER_BASE}/napl-reviewer"

Then launch from the extension panel. The extension picks up the
environment variable from the current shell session.

JetBrains IDEs (PyCharm, IntelliJ, WebStorm)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Option 1 — Built-in terminal**

Open the built-in terminal (``Alt+F12``) and call your switcher
function::

   tester

**Option 2 — Run configurations**

Create a *Shell Script* run configuration for each agent:

#. Go to **Run → Edit Configurations**.
#. Click **+** and choose **Shell Script**.
#. Set **Script text** to ``copilot`` (or whichever agent you want).
#. Name it ``NAPL: Pair Programmer``.
#. Repeat for each agent.

You can now launch any agent from the green run button dropdown.

Running Multiple Agents Side by Side
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open two terminal panels and start a different agent in each::

   # Terminal 1
   copilot       # writing the feature

   # Terminal 2
   reviewer      # reviewing the same files simultaneously

Each session has its own ``ANTHROPIC_BASE_URL`` because the shell
functions set it as a local export within that shell process. The two
agents operate independently and do not share context — which is
intentional.

.. tip::

   A practical three-agent workflow for a feature branch:

   1. ``copilot`` — implement the feature.
   2. ``tester`` — write the test suite against the implementation.
   3. ``reviewer`` — review both the implementation and the tests
      before you open the pull request.

   All three can be open simultaneously in separate terminal tabs.

----

.. _custom-agents:

Creating Your Own Agents
------------------------

Any programmer can create a project-specific or role-specific agent by
writing a new YAML file, changing three fields, and running
``smarter apply`` followed by ``smarter deploy``.

The minimal changes required from any of the presets above:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - What to change
   * - ``metadata.name``
     - A unique lowercase identifier — becomes part of the endpoint URL
   * - ``metadata.description``
     - A one-line description of this agent's purpose
   * - ``spec.config.defaultSystemRole``
     - The persona and behaviour instructions for this agent
   * - ``spec.config.defaultTemperature``
     - Lower (0.0–0.2) for precise tasks; higher (0.3–0.5) for creative
       or explanatory tasks

Some ideas for additional NAPL-specific agents:

* **napl-oracle-dba** — specialised in Oracle PL/SQL, stored procedures,
  and query optimisation for the axiUm and GDP data layers.
* **napl-security** — focused on OWASP Top 10, input sanitisation, and
  reviewing code for injection vulnerabilities.
* **napl-crystal** — understands Crystal Reports formula syntax and
  helps write or debug report expressions.
* **napl-onboarder** — walks new team members through the codebase,
  explains architecture decisions, and answers "why does this exist?"
  questions.

Once created, add a new shell function to your profile following the
same pattern as the existing switcher functions, reload your shell, and
the new agent is ready to use.

----

.. rubric:: Maintained by

NAPL IT — Custom Programming Area Go-Live Project

*Questions? Open a ticket in the NAPL IT Service Desk under
"AI Tools / Claude Code".*

----

.. rubric:: Developer Note — Integrating this file into the Smarter docs build

.. code-block:: python

   # docs/conf.py — required settings to match the Smarter RTD theme and
   # YAML syntax highlighting shown in the platform documentation.

   html_theme = "sphinx_rtd_theme"
   pygments_style = "monokai"

   extensions = [
       "sphinx.ext.autosectionlabel",
       "sphinx.ext.githubpages",
   ]

   autosectionlabel_prefix_document = True

Place this file at::

   docs/en/getting-started/napl-programmers.rst

Add it to the appropriate ``toctree`` in ``docs/en/index.rst``::

   .. toctree::
      :maxdepth: 2
      :caption: Getting Started

      getting-started/napl-programmers
