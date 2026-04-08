.. _napl-adding-llm-provider:

=========================================================
How-To: Adding Anthropic as an LLM Provider to Smarter
=========================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

Goal
====

Register Anthropic as an LLM provider on your organization's Smarter platform
so that Claude models are available to chatbots, the Prompt Engineer Workbench,
and developer tooling such as Claude Code.

By the end of this tutorial you will have two verified Claude models —
**Claude Opus** and **Claude Sonnet** — ready for use across the platform.

Prerequisites
=============

Before you begin, confirm that you have:

- **Smarter v0.11.0 or later**, deployed and accessible.
- An **administrator-level** Smarter account with permission to manage providers.
- The **Smarter CLI** installed and authenticated.
  See :doc:`/smarter-framework/smarter-cli` for installation instructions.
- A text editor. VS Code with the
  `Smarter YAML extension <https://marketplace.visualstudio.com/items?itemName=querium.smarter-manifest>`_
  provides autocomplete and validation for manifest files.

.. note::

   You do **not** need an Anthropic API key on your personal machine. The key
   is configured once at the platform level and stored securely in Smarter.
   Individual developers never handle provider credentials directly.

Setup
=====

Smarter supports two categories of LLM providers.

**Built-in providers** are pre-initialized automatically during deployment
and only require an API key in ``.env``:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Provider
     - Environment Variable
     - API Key Console
   * - OpenAI *(required)*
     - ``SMARTER_OPENAI_API_KEY``
     - `platform.openai.com/api-keys <https://platform.openai.com/api-keys>`_
   * - GoogleAI
     - ``SMARTER_GEMINI_API_KEY``
     - `aistudio.google.com/app/apikey <https://aistudio.google.com/app/apikey>`_
   * - MetaAI
     - ``SMARTER_LLAMA_API_KEY``
     - `console.apillm.com <https://console.apillm.com/en/dashboard/api-token>`_

**Additional providers** require both an API key in ``.env`` **and** a
Provider manifest applied via the CLI:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Provider
     - Environment Variable
     - API Key Console
   * - **Anthropic**
     - ``SMARTER_ANTHROPIC_API_KEY``
     - `console.anthropic.com <https://console.anthropic.com/>`_
   * - Cohere
     - ``SMARTER_COHERE_API_KEY``
     - `dashboard.cohere.com/api-keys <https://dashboard.cohere.com/api-keys>`_
   * - Fireworks
     - ``SMARTER_FIREWORKS_API_KEY``
     - `fireworks.ai/api-keys <https://fireworks.ai/api-keys/>`_
   * - Mistral
     - ``SMARTER_MISTRAL_API_KEY``
     - `console.mistral.ai/api-keys <https://console.mistral.ai/api-keys/>`_
   * - TogetherAI
     - ``SMARTER_TOGETHERAI_API_KEY``
     - `together.ai/settings/api-keys <https://together.ai/settings/api-keys>`_

This tutorial walks through adding **Anthropic** as an additional provider.

Concept Overview
================

Smarter manages every resource — providers, chatbots, plugins — through
declarative YAML files called **SAM** (Smarter API Manifests). This pattern
is modeled on Kubernetes: you describe the desired state in a file and
``smarter apply`` makes it happen.

A Provider manifest has four sections:

- ``apiVersion`` — always ``smarter.sh/v1``.
- ``kind`` — set to ``Provider``.
- ``metadata`` — a unique name, human-readable description, and version.
- ``spec`` — the provider configuration: which backend and which model.

When you apply a manifest, Smarter registers the provider and automatically
runs verification checks against the provider's API. Once verification passes,
the provider is marked active and its models become available platform-wide.

Step-by-Step
============

Step 1: Obtain an Anthropic API Key
------------------------------------

1. Sign in at `console.anthropic.com <https://console.anthropic.com/>`_.
2. Navigate to **Settings > API Keys > Create Key**.
3. Give the key a descriptive name (e.g. ``smarter-napl-prod``).
4. Copy the key immediately — it is displayed only once.

.. danger::

   Never commit API keys to version control or share them in plain text.
   The key will be stored in the Smarter ``.env`` file on the server, which
   should be excluded from source control.

Step 2: Add the Key to the Smarter Environment
------------------------------------------------

Open the ``.env`` file at the root of your Smarter deployment and add:

.. code-block:: bash

   SMARTER_ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Restart the application so it picks up the new credential:

.. code-block:: bash

   make restart

Step 3: Generate a Manifest Template
--------------------------------------

Use the CLI to print a valid starter manifest:

.. code-block:: bash

   smarter manifest provider

Review the output to understand the expected structure before writing your
own manifests.

Step 4: Create the Provider Manifests
--------------------------------------

Create one manifest per model. We will register two Claude models so the
team can evaluate cost-versus-quality trade-offs in the Workbench.

Create a file named ``anthropic-opus.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-opus
     description: Anthropic Claude Opus 4 - high-capability model
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-opus-4-5

Create a second file named ``anthropic-sonnet.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-sonnet
     description: Anthropic Claude Sonnet 4 - balanced speed and quality
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-sonnet-4-6

.. note::

   Model identifiers are **case-sensitive** and must match the names
   published by Anthropic exactly. For the complete manifest field reference,
   see :doc:`/smarter-resources/provider/sam`.

Step 5: Apply the Manifests
-----------------------------

.. code-block:: bash

   smarter apply -f anthropic-opus.yaml
   smarter apply -f anthropic-sonnet.yaml

Smarter registers each provider and begins asynchronous verification checks.

Step 6: Verify the Providers
------------------------------

.. code-block:: bash

   smarter describe provider anthropic-opus
   smarter describe provider anthropic-sonnet

Look for a ``status`` section showing ``verified: true`` in each output.
If the status shows ``pending``, wait 30 seconds and run the command again —
verification checks are asynchronous.

You can also confirm via the web console: open the **Providers** page in the
left sidebar. Both ``anthropic-opus`` and ``anthropic-sonnet`` should appear
with an active status indicator.

Proof of Concept
================

Run the following commands to confirm end-to-end success:

.. code-block:: bash

   smarter describe provider anthropic-opus
   smarter describe provider anthropic-sonnet

Expected output for each provider (abbreviated):

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-opus
     description: Anthropic Claude Opus 4 - high-capability model
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-opus-4-5
   status:
     verified: true
     active: true

Both providers showing ``verified: true`` and ``active: true`` confirms that
Smarter has established a live connection to the Anthropic API and the models
are ready for use in chatbots and the Workbench.

.. tip::

   With both providers active, you can create two chatbots — one backed by
   Opus and one by Sonnet — and compare their responses to the same prompt
   in the Workbench. This is a practical way to evaluate which model best
   fits each use case before rolling it out to the programming team.

Troubleshooting
===============

**"API key not found" on startup**
   The ``SMARTER_ANTHROPIC_API_KEY`` variable is missing from ``.env`` or
   the application was not restarted after adding it. Run ``make restart``.

**Provider status shows "verification failed"**
   The API key is invalid, expired, or has been revoked. Generate a new key
   at `console.anthropic.com <https://console.anthropic.com/>`_ and update
   the ``.env`` file.

**"Model not found" when applying a manifest**
   The ``model`` value does not match the provider's published identifier.
   Double-check the spelling and casing. Anthropic model names use lowercase
   with hyphens (e.g. ``claude-opus-4-5``).

**YAML validation errors**
   Indentation is almost always the cause. Run ``smarter manifest provider``
   to compare your file against a known-good template. YAML requires spaces,
   not tabs.

**Provider appears in CLI but not in the web console**
   Refresh the browser. If it still does not appear, confirm that your
   Smarter account has administrator privileges.

**"billing_not_active" or rate limit errors**
   Your Anthropic account does not have billing configured, or the API key
   belongs to a free-tier account that has exhausted its quota. Add a payment
   method at
   `console.anthropic.com/settings/billing <https://console.anthropic.com/settings/billing>`_.

**API key starts with ``sk-ant-oat01-``**
   OAuth tokens (``sk-ant-oat01-``) are not valid for direct API calls.
   Ensure the key starts with ``sk-ant-api03-``. Generate a standard API key
   from the Anthropic console.

.. seealso::

   - :doc:`/smarter-resources/smarter-provider` — Provider technical reference
   - :doc:`/smarter-resources/provider/sam` — SAM manifest field reference
   - :doc:`/smarter-resources/provider/api` — Provider REST API
   - `Anthropic API Documentation <https://docs.anthropic.com/>`_
   - `Anthropic Model List <https://docs.anthropic.com/en/docs/about-claude/models>`_
