.. _getting-started-claude-code-marvintran:

===========================================================
Getting Started: Using Claude Code with Smarter at NAPL
===========================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

Goal
====

We will use Claude Code with Smarter to create a virtual CoPilot coding pair
for day-to-day development work at Northern Aurora Power & Light (NAPL). By the
end of this tutorial, you will have configured Anthropic as an LLM provider in
Smarter, created a Chatbot resource backed by Claude, connected Claude Code to
route through Smarter, and verified the full pipeline with a working
proof-of-concept prompt.

Prerequisites
=============

This tutorial assumes you already have the following:

- A Smarter account (provided by your team lead) and the ability to log in to
  the Smarter web console
- The **Smarter CLI** (``smarter``) installed and authenticated on your
  workstation — see `Smarter CLI documentation <https://platform.smarter.sh/docs/>`_
- **Claude Code** installed (``npm install -g @anthropic-ai/claude-code``)
- A terminal emulator (PowerShell, bash, or zsh)
- ``git`` installed and configured with your GitHub credentials
- Familiarity with YAML syntax and command-line tooling

.. note::

   Infrastructure provisioning of the Smarter Kubernetes cluster, IDE
   integration, and accounting cost-code setup are handled by other teams and
   are **out of scope** for this tutorial.

Setup
=====

Before you begin the step-by-step workflow, confirm the following items are
ready on your machine.

1. **Verify Smarter CLI connectivity.** Run::

      smarter version

   You should see the server version and your authenticated username. If not,
   re-authenticate with ``smarter login``.

2. **Verify Claude Code is installed.** Run::

      claude --version

   You should see a version string such as ``claude-cli/2.x.x``.

3. **Obtain an Anthropic API key.** Navigate to
   `console.anthropic.com <https://console.anthropic.com/>`_, create an API key
   for your NAPL project, and store it securely. You will need this key in
   Step 2 below.

4. **Confirm network access.** Your workstation must be able to reach both the
   NAPL Smarter endpoint and ``api.anthropic.com`` (or the on-premise proxy
   address provided by the infrastructure team).

Concept Overview
================

Understanding the following concepts will make the step-by-step section much
easier to follow.

Smarter Manifests
-----------------

Smarter manages all AI resources — chatbots, plugins, models, users — through
**YAML manifests**. A manifest is a declarative document, inspired by
Kubernetes, with four main sections:

``apiVersion``
   Identifies the manifest schema version (e.g., ``smarter.sh/v1``).

``kind``
   The type of resource (e.g., ``Chatbot``, ``Plugin``, ``User``).

``metadata``
   Human-readable identifiers: ``name``, ``description``, ``version``.

``spec``
   The configuration payload — LLM provider details, prompt settings,
   functions, plugins, and appearance.

``status``
   Read-only state managed by the Smarter API.

You author manifests locally, then apply them with the Smarter CLI. Smarter
reconciles the desired state in the manifest with the actual state of your
cloud resources.

LLM Providers in Smarter
-------------------------

Smarter is **LLM-provider-agnostic**. Out of the box it integrates with
OpenAI, Google, and HuggingFace, among others. Adding a new provider — such as
Anthropic — means telling Smarter how to reach the provider's API, which model
to use, and what credentials to present. All of this is expressed in the
``spec`` section of a Chatbot manifest.

Key data points Smarter needs for any LLM provider:

- **Provider name** — a label Smarter uses internally (e.g., ``anthropic``).
- **Model identifier** — the specific model string
  (e.g., ``claude-sonnet-4-5-20250929``).
- **API base URL** — the endpoint Smarter calls
  (e.g., ``https://api.anthropic.com/v1``).
- **API key** — authentication credential, stored as a Smarter secret.
- **Default parameters** — ``temperature``, ``max_tokens``, and other tuning
  knobs surfaced in the manifest's ``default*`` fields.

Claude Code
-----------

Claude Code is Anthropic's agentic coding assistant. It runs in your terminal,
reads and modifies files in your working directory, executes shell commands, and
manages Git workflows — all through natural-language conversation. When routed
through Smarter, every Claude Code request benefits from Smarter's centralized
authentication, cost tracking, audit logging, and prompt moderation.

Step-by-Step
============

Step 1 — Scaffold a Chatbot Manifest
-------------------------------------

Use the Smarter CLI to generate a blank Chatbot manifest::

   smarter manifest chatbot -o yaml > napl-claude-copilot.yaml

This produces a YAML file pre-populated with every available field and
sensible defaults. Open it in your editor.

Step 2 — Configure Anthropic as the LLM Provider
-------------------------------------------------

Edit ``napl-claude-copilot.yaml`` so that the ``metadata`` and ``spec``
sections reflect the Anthropic / Claude configuration. Below is a minimal
working example — adjust values to match your NAPL environment:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Chatbot
   metadata:
     name: NAPLClaudeCopilot
     description: >-
       Claude-powered CoPilot for NAPL custom programming.
     version: 1.0.0
   spec:
     # ---- LLM provider settings ----
     defaultProvider: anthropic
     defaultModel: claude-sonnet-4-5-20250929
     defaultTemperature: 0.2
     defaultMaxTokens: 4096

     # ---- Appearance (optional) ----
     appName: NAPL CoPilot
     appWelcomeMessage: >-
       Welcome to the NAPL Claude CoPilot.
       Ask me anything about our codebase.
     appExamplePrompts:
       - "Refactor the billing module to use async I/O."
       - "Write unit tests for the outage-report parser."
       - "Explain the legacy VB6 COM bridge in plain English."

     # ---- State ----
     state: deployed

.. important::

   Do **not** paste your Anthropic API key directly into the manifest. Smarter
   manages secrets separately. You will register the key in the next step.

Step 3 — Register Your Anthropic API Key
-----------------------------------------

Store your API key as a Smarter secret so Smarter can authenticate with
Anthropic on your behalf::

   smarter create secret anthropic-api-key \
     --value "sk-ant-XXXXXXXXXXXXXXXXXXXX"

Replace the placeholder with your actual key from
``console.anthropic.com``.

Step 4 — Apply the Manifest
----------------------------

Deploy your new Chatbot resource::

   smarter apply -f napl-claude-copilot.yaml

Smarter will validate the manifest, create the Chatbot, and set its state to
``deployed``. Confirm with::

   smarter get chatbots

You should see ``NAPLClaudeCopilot`` listed with a ``deployed`` status.

Step 5 — Point Claude Code at Smarter
--------------------------------------

Claude Code needs two environment variables to route its requests through
Smarter instead of calling Anthropic directly:

.. code-block:: bash

   export ANTHROPIC_BASE_URL="https://smarter.napl.internal/v1"
   export ANTHROPIC_API_KEY="sk-ant-XXXXXXXXXXXXXXXXXXXX"

.. tip::

   For persistence across terminal sessions, add these exports to your shell
   profile (``~/.bashrc``, ``~/.zshrc``, or your PowerShell ``$PROFILE``).

Smarter acts as an **LLM gateway**: it receives the Anthropic-formatted
request from Claude Code, applies enterprise policies (audit, cost tracking,
content moderation), and forwards the call to the Anthropic API.

Step 6 — Verify in the Smarter Web Console
-------------------------------------------

Open the Smarter web console, navigate to your ``NAPLClaudeCopilot`` Chatbot,
and enter the Sandbox. Type a test prompt such as::

   Explain what a Smarter manifest is in two sentences.

In the Sandbox you can inspect the full request/response cycle — prompt
pre-processing, token counts, LLM response, and any function or plugin
invocations. This visibility is invaluable during development.

Proof of Concept
================

With everything wired up, open a terminal in one of your NAPL project
repositories and launch Claude Code::

   cd ~/repos/napl-billing-service
   claude

At the Claude Code prompt, type::

   Read the README and summarize what this project does, then suggest three
   improvements to the test suite.

**Expected result:**

- Claude Code reads files from your working directory.
- The request routes through Smarter (visible in Smarter's audit log).
- Claude responds with a project summary and actionable test-suite
  recommendations.
- Running ``smarter logs NAPLClaudeCopilot`` shows the prompt, token usage,
  and cost for the interaction.

If you see all of the above, your Claude Code + Smarter integration is fully
operational. You are now ready to use Claude as your virtual CoPilot.

Troubleshooting
===============

**"Unable to connect to API (ConnectionRefused)"**
   Claude Code cannot reach Smarter. Verify ``ANTHROPIC_BASE_URL`` is set
   correctly. Check that your VPN or network proxy allows traffic to the
   Smarter endpoint. Run ``curl -s $ANTHROPIC_BASE_URL/health`` to test
   connectivity.

**"Authentication error" or 401 responses**
   Your API key may be invalid or the Smarter secret was not created. Re-run
   ``smarter create secret anthropic-api-key --value "..."`` with a valid key.
   Also confirm Claude Code's ``ANTHROPIC_API_KEY`` matches what Smarter
   expects.

**Manifest validation fails on apply**
   Double-check YAML indentation — YAML is whitespace-sensitive. Use the
   ``smarter manifest chatbot -o yaml`` output as a reference. Ensure
   ``apiVersion`` is ``smarter.sh/v1`` and ``kind`` is ``Chatbot``.

**Claude Code responds but Smarter shows no logs**
   Claude Code may be bypassing Smarter and calling Anthropic directly.
   Confirm ``ANTHROPIC_BASE_URL`` is set in the *same* terminal session
   where you launched ``claude``. Run ``env | grep ANTHROPIC`` to verify.

**High latency or timeouts**
   If Smarter is deployed on-premise, confirm the Kubernetes cluster has
   adequate resources. Check ``smarter status`` for service health. Increase
   ``defaultMaxTokens`` only if needed — larger values increase response time
   and cost.

**"Model not found" error**
   Verify the model string in your manifest matches a model available on your
   Anthropic plan. At the time of writing, recommended models include
   ``claude-sonnet-4-5-20250929`` and ``claude-haiku-4-5-20251001``. Consult
   Anthropic's model documentation for the current list.

Saving Your Work to GitHub
==========================

Once your tutorial RST file and any supporting manifests are complete, push
them to your fork of the Smarter repository::

   cd /path/to/your/smarter-fork
   git add .
   git commit -m "docs: add Sphinx tutorials for UBC FENT20"
   git push

Your work is now synchronized with your remote repository on GitHub.

.. seealso::

   - `Smarter Platform Documentation <https://platform.smarter.sh/docs/>`_
   - `Smarter Technical Documentation <https://docs.smarter.sh/>`_
   - `Anthropic Claude Code Documentation <https://docs.anthropic.com/en/docs/claude-code>`_
   - `Smarter CLI Repository <https://github.com/smarter-sh/smarter-cli>`_

*Created with help from ClaudeAI*
