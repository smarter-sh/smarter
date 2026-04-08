.. _claude-code-with-smarter:

Claude Code with Smarter: Adding Anthropic and Getting Started
==============================================================

*Northern Aurora Power & Light (NAPL) — Custom Programming Area*

This tutorial covers two things in one place: how to register **Anthropic**
as an LLM provider in Smarter, and how NAPL programmers get up and running
with **Claude Code** as a virtual CoPilot pair-programming partner.

.. contents:: Table of Contents
   :depth: 2
   :local:


----

Part 1 — Adding Anthropic as an LLM Provider
=============================================

Goal
----

Register Anthropic and its ``claude-sonnet-4-6`` model in the Smarter
platform so that Claude Code is available as a managed LLM resource for
all NAPL developers.

.. note::

   Anthropic is one of the officially supported "legacy" providers in Smarter
   and is stable.  The steps below apply equally to any new third-party
   provider you may want to onboard in the future.


Prerequisites
-------------

* The Smarter platform is installed and reachable (see the
  `Smarter Installation Guide <https://docs.smarter.sh/en/latest/smarter-platform/installation.html>`__).
* The Smarter CLI (``smarter``) is installed and configured.
  Verify with:

  .. code-block:: bash

     smarter version
     smarter whoami

* You hold a **Smarter Account** with provider-management permissions.
* You have an **Anthropic API key** (``sk-ant-…``).
  Obtain one at `console.anthropic.com <https://console.anthropic.com/>`__.


Overview
--------

Adding a provider involves three Smarter resources, applied in order:

1. **Secret** — stores your Anthropic API key securely.
2. **Provider** — registers Anthropic as an LLM provider and links it to
   the Secret.
3. **ProviderModel** — registers ``claude-sonnet-4-6`` as the default model.

All resources are declared as YAML manifest files and applied with
``smarter apply``.


Step 1 — Create the API Key Secret
------------------------------------

Create a file named ``anthropic-secret.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Secret
   metadata:
     name: anthropic-api-key
     description: Anthropic API key for Claude models
     version: 1.0.0
     tags:
       - anthropic
       - llm
   spec:
     config:
       description: "Production Anthropic API key.  Keep this value private."
       value: sk-ant-YOUR_API_KEY_HERE   # replace with your real key

Apply it:

.. code-block:: bash

   smarter apply -f anthropic-secret.yaml

.. warning::

   Never commit a manifest that contains a real API key to version control.
   Use an environment variable or a secrets-management tool to substitute
   the value at apply time.


Step 2 — Create the Provider Manifest
----------------------------------------

Create a file named ``anthropic-provider.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: Anthropic
     description: >
       Anthropic PBC — AI safety company and maker of the Claude family of
       large language models.
     version: 1.0.0
     tags:
       - anthropic
       - claude
       - llm
   spec:
     base_url: https://api.anthropic.com
     connectivity_test_path: /v1/models
     website_url: https://www.anthropic.com
     docs_url: https://docs.anthropic.com
     contact_email: support@anthropic.com
     support_email: support@anthropic.com
     terms_of_service_url: https://www.anthropic.com/legal/terms
     privacy_policy_url: https://www.anthropic.com/legal/privacy
     api_key: anthropic-api-key          # references the Secret created above

Apply it:

.. code-block:: bash

   smarter apply -f anthropic-provider.yaml

After applying, Smarter runs automated verification checks (API connectivity,
contact email, ToS URL, etc.).  Confirm the provider is verified:

.. code-block:: bash

   smarter describe provider Anthropic


Step 3 — Register the Claude Code Model
-----------------------------------------

Create a file named ``anthropic-claude-code-model.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: ProviderModel
   metadata:
     name: claude-sonnet-4-6
     description: >
       Claude Sonnet 4.6 — the model powering Claude Code.
       Optimised for agentic coding tasks, tool use, and long-context
       reasoning.
     version: 1.0.0
   spec:
     provider: Anthropic
     is_default: true
     max_completion_tokens: 8096
     temperature: 1.0
     top_p: 1.0
     supports_text_input: true
     supports_text_generation: true
     supports_streaming: true
     supports_tools: true
     supports_summarization: true
     supports_translation: true
     supports_image_input: false
     supports_audio_input: false
     supports_embedding: false
     supports_fine_tuning: false
     supports_search: false
     supports_code_interpreter: true
     supports_image_generation: false
     supports_audio_generation: false

Apply it:

.. code-block:: bash

   smarter apply -f anthropic-claude-code-model.yaml


Step 4 — Verify the Full Provider Setup
-----------------------------------------

List all registered providers to confirm Anthropic appears:

.. code-block:: bash

   smarter get providers

Inspect the Anthropic provider in detail:

.. code-block:: bash

   smarter describe provider Anthropic -o yaml

List models registered under Anthropic:

.. code-block:: bash

   smarter get providers Anthropic models

The ``describe`` command should return a ``status`` block showing:

.. code-block:: yaml

   status:
     is_active: true
     is_verified: true
     status: verified


Troubleshooting (Provider)
--------------------------

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Symptom
     - Resolution
   * - ``status: failed`` after apply
     - Check that ``base_url`` is reachable from your cluster and that the
       Secret value is a valid Anthropic API key (starts with ``sk-ant-``).
   * - ``Secret not found`` error
     - Apply ``anthropic-secret.yaml`` **before** ``anthropic-provider.yaml``.
       The Provider manifest references the Secret by name.
   * - ``Unauthorized`` from Anthropic API
     - The API key may be inactive.  Rotate the key in the Anthropic console
       and update the Secret: ``smarter apply -f anthropic-secret.yaml``.
   * - Provider stuck at ``status: verifying``
     - Verification runs asynchronously.  Wait 60 seconds, then re-run
       ``smarter describe provider Anthropic``.  For persistent issues:
       ``smarter logs provider Anthropic``.


----

Part 2 — Getting Started: Claude Code for NAPL Programmers
===========================================================

Goal
----

Use **Claude Code** with the NAPL **Smarter** platform to create an
AI-assisted coding environment in which every developer has a virtual CoPilot
pair-programming partner powered by Anthropic's Claude family of models.

By the end of this section you will:

* Connect your local development environment to the NAPL Smarter instance.
* Verify that Anthropic / Claude Code is available as a provider.
* Deploy a personal Chatbot and chat with Claude Code from the terminal.


Prerequisites
-------------

You are assumed to be comfortable with:

* The Unix/Windows command line and basic shell scripting.
* A code editor — VS Code is recommended; install the
  `Smarter Manifest Extension <https://marketplace.visualstudio.com/items?itemName=Querium.smarter-manifest>`__
  for YAML syntax highlighting.
* ``git`` basics (clone, commit, push).
* REST APIs — knowing what a base URL and API key are is sufficient.

You do **not** need prior Kubernetes or cloud infrastructure experience.
The infrastructure team has already deployed Smarter; your job is to
connect to it.


Setup
-----

1. **Obtain your Smarter account credentials**

   Your manager or the Smarter platform administrator will provide:

   * The NAPL Smarter API endpoint URL (e.g., ``https://smarter.napl.internal``).
   * Your personal Smarter API key (a long alphanumeric string).

2. **Install the Smarter CLI**

   Follow the instructions at `smarter.sh/cli <https://smarter.sh/cli>`__
   for your operating system (Windows, macOS, or Linux).

   Confirm the install:

   .. code-block:: bash

      smarter version

3. **Configure the CLI**

   .. code-block:: bash

      smarter configure

   When prompted, enter:

   * **API key** — your personal Smarter API key.
   * **Environment** — ``prod`` (default; only change if told otherwise by IT).

   This writes ``~/.smarter/config.yaml``.  Verify it works:

   .. code-block:: bash

      smarter whoami

   You should see your NAPL user name and account details.

4. **Install Claude Code (optional local client)**

   Claude Code is Anthropic's AI coding assistant CLI.  Install it globally
   via npm:

   .. code-block:: bash

      npm install -g @anthropic-ai/claude-code

   Point it at your Smarter instance so requests route through the
   corporate platform instead of directly to Anthropic:

   .. code-block:: bash

      export ANTHROPIC_BASE_URL=https://smarter.napl.internal/api/v1/anthropic
      export ANTHROPIC_API_KEY=<your-smarter-api-key>

   Add these exports to your ``~/.bashrc`` or ``~/.zshrc`` to make them
   permanent.


Concept Overview
----------------

Smarter is an enterprise-grade, on-premise LLM hosting and orchestration
platform.  Before using Claude Code you should understand four core ideas:

Smarter API Manifests (SAM)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

All Smarter resources — providers, chatbots, plugins, secrets — are declared
as human-readable **YAML manifest files** (think Kubernetes manifests).
You apply them with the CLI:

.. code-block:: bash

   smarter apply -f my-manifest.yaml

The ``kind`` field selects the resource type:
``Secret``, ``Provider``, ``ProviderModel``, ``Chatbot``, ``Plugin``, etc.

Providers and Models
~~~~~~~~~~~~~~~~~~~~

A **Provider** represents a third-party LLM API (e.g., Anthropic).
A **ProviderModel** is a specific model offered by that provider
(e.g., ``claude-sonnet-4-6``).  Smarter stores the API credentials in a
**Secret** resource so they are never hard-coded in application code.

The Smarter CLI
~~~~~~~~~~~~~~~

The CLI uses a *verb-noun* pattern identical to ``kubectl``:

.. code-block:: text

   smarter [command] [resource] [name] [flags]

Key commands you will use daily:

* ``smarter apply -f <file>`` — create or update a resource.
* ``smarter get providers`` — list available LLM providers.
* ``smarter describe provider Anthropic`` — inspect a provider.
* ``smarter chat <chatbot-name>`` — start an interactive chat session.

Claude Code and Smarter
~~~~~~~~~~~~~~~~~~~~~~~

Claude Code is Anthropic's terminal-native AI coding assistant.  When
integrated with Smarter it routes all LLM requests through the corporate
Smarter instance.  This means:

* **API key management** is centralised — you use your Smarter key, not a
  personal Anthropic key.
* **Cost tracking** is automatic — token consumption is billed against NAPL's
  cost codes, not individual employee accounts.
* **Access control** is enforced — the platform team can grant, revoke, or
  rate-limit access without touching individual workstations.


Step-by-Step
------------

Step 1 — Verify Anthropic is Available
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Confirm the IT team has already registered Anthropic as a provider:

.. code-block:: bash

   smarter get providers

Expected output (abbreviated):

.. code-block:: text

   NAME         STATUS     VERIFIED
   Anthropic    active     true
   OpenAI       active     true

If ``Anthropic`` is missing or not verified, contact the platform team and
reference Part 1 of this tutorial.

Step 2 — Inspect the Claude Code Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   smarter describe provider Anthropic -o yaml

Look for ``claude-sonnet-4-6`` in the ``models`` list.  Note the
``is_default`` flag — this is the model used unless you specify another.

Step 3 — Generate a Chatbot Manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the CLI to scaffold a Chatbot manifest pre-filled with defaults:

.. code-block:: bash

   smarter manifest chatbot -o yaml > my-claude-chatbot.yaml

Open ``my-claude-chatbot.yaml`` in your editor and update the key fields:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Chatbot
   metadata:
     name: my-claude-chatbot
     description: Personal Claude Code chatbot for NAPL dev work
     version: 1.0.0
   spec:
     provider: Anthropic
     model: claude-sonnet-4-6
     system_prompt: >
       You are an expert software engineer helping NAPL developers write
       clean, secure, and well-documented code.  Prefer Python and follow
       PEP 8.  Always explain what changed and why.

Step 4 — Apply and Deploy the Chatbot
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   smarter apply -f my-claude-chatbot.yaml
   smarter deploy chatbot my-claude-chatbot

Confirm it was created:

.. code-block:: bash

   smarter get chatbots

Step 5 — Chat with Claude Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Start an interactive terminal session:

.. code-block:: bash

   smarter chat my-claude-chatbot

Type a prompt to test:

.. code-block:: text

   > Write a Python function that reads a CSV file and returns a list of dicts.

You should receive a complete, working code snippet from Claude.

For day-to-day coding, start Claude Code directly in your project directory
(after setting the environment variables from Setup step 4):

.. code-block:: bash

   cd ~/my-project
   claude


Proof of Concept
----------------

A successful integration produces output like this when you run
``smarter chat my-claude-chatbot`` and send a test prompt:

.. code-block:: text

   You: Write a one-line Python function that returns True if a number is even.

   Claude: is_even = lambda n: n % 2 == 0

You can also verify platform health with:

.. code-block:: bash

   smarter status


Troubleshooting
---------------

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Symptom
     - Resolution
   * - ``smarter whoami`` returns ``Unauthorized``
     - Re-run ``smarter configure`` and double-check your API key.  Keys
       are case-sensitive.
   * - ``Provider Anthropic not found``
     - The provider has not been registered.  Contact the platform admin and
       reference Part 1 of this tutorial.
   * - ``Model claude-sonnet-4-6 not found``
     - The model manifest may not have been applied.  Ask the admin to run
       ``smarter get providers Anthropic models``.
   * - Chatbot applies but ``smarter chat`` hangs
     - Check your network route to the Smarter endpoint.  Run
       ``smarter status`` to confirm platform health.  VPN may be required
       if working remotely.
   * - Claude Code CLI says ``ANTHROPIC_BASE_URL not set``
     - Add the export lines from Setup step 4 to your shell profile and
       restart the terminal, or run ``source ~/.bashrc``.
   * - Responses are slow or time out
     - This is normal under heavy platform load.  Contact the platform team
       if latency exceeds 30 seconds consistently.


See Also
--------

* `Smarter Provider Reference <https://docs.smarter.sh/en/latest/smarter-resources/smarter-provider.html>`__
* `Smarter CLI Reference <https://docs.smarter.sh/en/latest/smarter-framework/smarter-cli.html>`__
* `Smarter Manifest Examples <https://ubc.smarter.sh/docs/manifests/>`__
* `Claude Code Documentation <https://docs.anthropic.com/en/docs/claude-code>`__
* `Anthropic API Reference <https://docs.anthropic.com/>`__
