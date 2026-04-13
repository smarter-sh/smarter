.. _getting-started-napl-programmers:

.. highlight:: yaml

Getting Started: Pair Programming with Claude on Smarter
=========================================================

.. meta::
   :description: Self-onboarding guide for NAPL programmers using Claude
                 via the Smarter CLI as a virtual CoPilot coding pair.
   :keywords: claude, smarter, anthropic, napl, copilot, chatbot, yaml

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
     - You are configuring the Smarter CLI for the first time
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
   * - 💻 IDE Usage
     - :ref:`ide-usage`
     - Using agents in VS Code, switching and running multiple at once
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

We will use **Claude** with the **Smarter** platform to create a set of
virtual CoPilot coding agents — each with a focused role — that you can
talk to directly from your terminal using the Smarter CLI. No additional
tools, no API keys, and no third-party clients are required.

By the end of this tutorial you will have:

* Created one or more Smarter Chatbot manifests configured to use
  Anthropic's Claude as their LLM provider.
* Deployed those Chatbots to the Smarter platform using the CLI.
* Started a live coding conversation with each agent using
  ``smarter chat``.
* Set up named shortcuts so you can switch between specialised roles —
  pair programmer, reviewer, tester, debugger, and doc writer — with a
  single command.

----

.. _why-this-approach:


Why This Approach
-----------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Benefit
     - What it means for you
   * - **One credential**
     - Your Smarter API key is all you need. No personal Anthropic
       account, no credit card, no key rotation. Access is revoked in
       one place when someone leaves.
   * - **Nothing extra to install**
     - ``smarter chat`` is the only client. No npm, no language
       runtimes, no IDE extensions.
   * - **Specialised agents**
     - Each manifest encodes a focused role and your team's coding
       standards. Every developer gets the same consistent behaviour
       without copy-pasting prompt templates.
   * - **Code stays inside NAPL**
     - All traffic routes through the on-premise Smarter gateway.
       Source code, schemas, and business logic never reach a public
       endpoint. TLS is enforced end-to-end.
   * - **Full audit trail**
     - Every prompt and response is logged with timestamp and user
       identity — a complete, tamper-evident record for compliance
       and internal review.
   * - **Enterprise access control**
     - API keys are scoped per user and team, expire automatically,
       and are revocable instantly. Role-based access controls who
       can use agents versus who can deploy them.
   * - **Centralised model governance**
     - NAPL IT controls which models are available. One manifest
       update rolls out a new model version to all teams instantly,
       or pins a version if needed. Developers cannot connect to
       unapproved endpoints.
   * - **Cost visibility**
     - Token usage is attributed to your team's cost code.
       Per-team budgets with alerts prevent unexpected overruns.


----

.. _prerequisites:

Prerequisites
-------------

You already have a Smarter account and know how to log in. You are also
expected to be comfortable with:

* **Terminal usage** — basic shell commands and editing
  ``~/.bashrc`` / ``~/.zshrc``.
* **YAML** — indentation, key/value pairs, and string quoting.
* **The Smarter CLI** — installed and available on your ``PATH``.

.. note::

   You do **not** need a personal Anthropic account, npm, Node.js, or
   any third-party client. The Smarter CLI is the only tool required
   beyond your existing development environment.

----

.. _setup:

Setup
-----

Configure the Smarter CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have not yet configured the CLI, run::

   smarter configure

Enter your API key and account number from your welcome e-mail when
prompted. Verify the configuration is correct::

   smarter whoami

This should return your username and account number.

Confirm Anthropic is available
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Verify that the Anthropic provider is enabled on your Smarter
installation::

   smarter get provider -o yaml

You should see ``anthropic`` listed as an available provider. If it is
missing, contact NAPL IT.

----

.. _concept-overview:

Concept Overview
----------------

How Smarter Manages LLM Providers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Smarter is a **provider-agnostic** platform. The LLM that backs any
given Chatbot is determined by two fields in its YAML manifest:
``provider`` and ``defaultModel``. Anthropic is a supported legacy
provider alongside OpenAI, GoogleAI, MetaAI, and DeepSeek. Switching
from OpenAI to Claude requires changing exactly these two fields:

.. code-block:: yaml

   provider: anthropic                       # was "openai"
   defaultModel: claude-sonnet-4-5-20250929  # was "gpt-4-turbo"

Everything else — plugins, system role, UI configuration, token limits
— is identical regardless of which provider backs the Chatbot.

The Smarter Chatbot Manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A Smarter manifest is a YAML file that describes a resource. You apply
it with ``smarter apply -f <file>`` and Smarter creates or updates the
resource to match. The manifest structure follows the same
``apiVersion / kind / metadata / spec`` pattern used throughout the
platform — familiar if you have worked with Kubernetes.

The ``smarter chat`` Command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``smarter chat --name <chatbot-name>`` opens an interactive session
with a deployed Chatbot directly in your terminal. You type your
message, press Enter, and Claude responds — all through the Smarter
gateway. No browser, no separate client, no additional setup.

.. code-block:: text

   Your terminal
        │
        │  smarter chat --name napl-copilot
        ▼
   Smarter CLI  ──►  Smarter Gateway  ──►  Anthropic  ──►  Claude

Specialised Agents via System Prompts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``defaultSystemRole`` field in the manifest is the persona and
behaviour instruction for the agent. By deploying multiple Chatbots
with different system roles — each with a unique ``name`` — you create
a roster of specialised coding agents that you can switch between
instantly. The only difference between a pair programmer and a code
reviewer is the words in that one field.

----

.. _step-by-step:

Step-by-Step
------------

Step 1 — Create your agent manifest files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a directory to keep your agent manifests organised::

   mkdir ~/napl-agents && cd ~/napl-agents

Five ready-to-use role presets are provided below. The fields that
differ between agents are ``metadata.name``, ``metadata.description``,
``spec.config.defaultSystemRole``, and ``spec.config.defaultTemperature``.
Everything else is identical.

.. _agent-copilot:

Agent CoPilot
----------------

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

Agent Reviewer
----------------

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
       appWelcomeMessage: Ready to review. Paste your code or describe what to check.
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

Agent Tester
----------------

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

Agent Debugger
----------------

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

Agent Doc Writer
----------------

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

Confirm each deployment::

   smarter describe chatbot napl-copilot -o yaml

Look for ``deployed: true`` in the output before proceeding.

Step 4 — Set up agent shortcuts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add the following aliases to your shell profile (``~/.bashrc`` or
``~/.zshrc``) so you can launch any agent by name:

.. code-block:: bash

   # ── NAPL agent shortcuts ──────────────────────────────────────────────
   alias copilot='smarter chat --name napl-copilot'
   alias reviewer='smarter chat --name napl-reviewer'
   alias tester='smarter chat --name napl-tester'
   alias debugger='smarter chat --name napl-debugger'
   alias docwriter='smarter chat --name napl-docwriter'

Reload your shell::

   source ~/.bashrc

You can now launch any agent from any directory:

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

Step 5 — Start a coding session
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Navigate to your project directory and launch an agent::

   cd ~/projects/my-service
   copilot

You will see the agent's welcome message and a prompt. Type your
request and press Enter::

   Add input validation to the create_patient() function in
   service.py. Raise ValueError if 'date_of_birth' is in the future.

Paste code snippets directly into the prompt, or describe what you
need in plain language. When you are done, type ``exit`` or press
``Ctrl+C`` to end the session.

.. tip::

   A practical three-agent workflow for a feature branch:

   1. ``copilot`` — implement the feature.
   2. ``tester`` — write the test suite against the implementation.
   3. ``reviewer`` — review both before you open the pull request.

----

.. _proof-of-concept:

Proof of Concept
----------------

Launch the pair programmer agent and give it a self-contained task::

   copilot

At the prompt, enter:

.. code-block:: text

   Write a Python function called calculate_bmi(weight_kg, height_m)
   that returns the BMI as a float rounded to one decimal place.
   It should raise ValueError if either argument is zero or negative.
   Then write the pytest tests covering the happy path, a boundary
   value, and both error cases.

**Expected outcome** — Claude returns a complete, working implementation
and test suite. Copy the output into your editor, run ``pytest``, and
confirm all tests pass.

If Claude responds with correct, runnable Python code, your full
pipeline is working: **your terminal → Smarter CLI → Smarter Gateway
→ Anthropic → Claude → back**.

----

.. _troubleshooting:

Troubleshooting
---------------

**``smarter apply`` fails with a provider error**

   Confirm ``provider: anthropic`` is spelled exactly as shown — it is
   case-sensitive. Also run ``smarter get provider -o yaml`` to verify
   the Anthropic provider is enabled on your installation. Contact
   NAPL IT if it is missing.

**``smarter chat`` returns** ``Chatbot not found``

   The Chatbot was applied but not deployed. Run::

      smarter deploy chatbot napl-copilot

   Then verify with ``smarter describe chatbot napl-copilot -o yaml``
   and confirm ``deployed: true``.

**``smarter whoami`` fails or returns an auth error**

   Your CLI is not configured or the API key has expired. Re-run::

      smarter configure

   Enter your API key and account number from your welcome e-mail.

**``smarter`` command not found**

   The Smarter CLI binary is not on your ``PATH``. Confirm where it was
   installed and add that directory to ``PATH`` in your shell profile,
   then reload::

      source ~/.bashrc

**Responses feel off-topic or ignore your coding context**

   The agent's ``defaultSystemRole`` may need tuning for your specific
   project. Edit the relevant YAML file, increment the ``version``
   field, and re-apply::

      smarter apply -f napl-copilot.yaml

   You do not need to redeploy after updating the system role — changes
   take effect on the next chat session.

**Session ends unexpectedly**

   This is usually a token limit issue. Reduce the length of your
   input, or break a large task into smaller steps across multiple
   sessions. You can also increase ``defaultMaxTokens`` in the manifest
   up to the model's supported maximum.

----

.. _ide-usage:

Using Agents in Your IDE
-------------------------

Because ``smarter chat`` runs entirely in a terminal, it works inside
any IDE without plugins, extensions, or special configuration. The
examples below use VS Code, but the same approach applies to any
JetBrains IDE or terminal-capable editor.

Opening an agent in VS Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open the integrated terminal with ``Ctrl+`` ` `` (Windows/Linux) or
``Cmd+`` ` `` (macOS), then call the agent alias you set up in Step 4::

   copilot

The agent starts inside VS Code, right next to your code. You can
paste code snippets from the editor directly into the terminal prompt,
and copy Claude's output back into your files.

Switching agents
~~~~~~~~~~~~~~~~~

To switch to a different agent, end the current session (``Ctrl+C`` or
type ``exit``) and start the new one::

   # end the pair programmer
   exit

   # start the reviewer instead
   reviewer

Each agent call is a fresh ``smarter chat`` session backed by its own
system prompt. The switch is instant.

Running multiple agents at the same time
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open additional terminal panels in VS Code by clicking the **+** icon
in the terminal toolbar, or pressing ``Ctrl+Shift+`` ``. Start a
different agent in each panel:``

.. code-block:: text

   ┌─────────────────────────┬─────────────────────────┐
   │  Terminal 1             │  Terminal 2             │
   │                         │                         │
   │  $ copilot              │  $ reviewer             │
   │  > writing the feature  │  > reviewing same files │
   └─────────────────────────┴─────────────────────────┘

Each panel runs an independent ``smarter chat`` session. The agents do
not share context with each other — which is intentional. The reviewer
sees only what you paste to it, not the pair programmer's in-progress
conversation.

.. tip::

   A practical three-terminal workflow for a feature branch:

   * **Terminal 1 —** ``copilot`` to implement the feature.
   * **Terminal 2 —** ``tester`` to write the test suite.
   * **Terminal 3 —** ``reviewer`` to review both before the pull
     request.

   All three run simultaneously. Switch focus between panels with
   ``Ctrl+`` ` `` and click the terminal name in the panel list.

----

.. _custom-agents:

Creating Your Own Agents
------------------------

Any programmer can create a project-specific or role-specific agent by
writing a new YAML file and running ``smarter apply`` and
``smarter deploy``. The minimal changes from any preset above:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - What to change
   * - ``metadata.name``
     - A unique lowercase identifier — used in ``smarter chat --name``
   * - ``metadata.description``
     - A one-line description of this agent's purpose
   * - ``spec.config.defaultSystemRole``
     - The persona and behaviour instructions for this agent
   * - ``spec.config.defaultTemperature``
     - Lower (0.0–0.2) for precise tasks; higher (0.3–0.5) for
       creative or explanatory tasks

Some ideas for additional NAPL-specific agents:

* **napl-oracle-dba** — specialised in Oracle PL/SQL, stored
  procedures, and query optimisation for the axiUm and GDP data layers.
* **napl-security** — focused on OWASP Top 10, input sanitisation,
  and reviewing code for injection vulnerabilities.
* **napl-crystal** — understands Crystal Reports formula syntax and
  helps write or debug report expressions.
* **napl-onboarder** — walks new team members through the codebase,
  explains architecture decisions, and answers "why does this exist?"
  questions.

Once created, add a matching alias to your shell profile::

   alias oracle='smarter chat --name napl-oracle-dba'

Reload your shell and the new agent is ready to use.

----

.. rubric:: Maintained by

NAPL IT — Custom Programming Area Go-Live Project

*Questions? Open a ticket in the NAPL IT Service Desk under
"AI Tools / Claude".*
