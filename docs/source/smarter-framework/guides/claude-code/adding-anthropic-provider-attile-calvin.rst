.. _adding-anthropic-provider-attile-calvin:

======================================================
How-To: Add Anthropic (Claude) as an LLM Provider
======================================================

Goal
====

We will register **Anthropic** as an LLM provider in Smarter and make two
Claude models available to every llmclient and to the Workbench. This is the
foundation NAPL's custom programming area needs before it can use Claude as a
coding assistant on the Smarter platform.

By the end, ``smarter describe provider`` will report both models as verified
and active.

.. note::

   *Claude Code* is Anthropic's agentic coding tool; it is not itself a model.
   What Smarter registers is the underlying Claude **model** that such tools
   call. This tutorial registers those models.


Prerequisites
=============

You should already be comfortable with:

- The command line and editing YAML files.
- Environment variables and ``.env`` files.
- Basic Docker and ``make`` usage on a running deployment.
- Kubernetes-style declarative resources (``apply`` / ``describe``). Smarter
  deliberately borrows this model.

You will also need:

- Smarter **v0.11.0 or later**, running and reachable.
- An **administrator-level** account on the Smarter web console.
- The `Smarter CLI <https://docs.smarter.sh/smarter-framework/smarter-cli.html>`_
  installed and authenticated.
- An Anthropic account with permission to create API keys.
- A text editor. VS Code with the Smarter YAML extension is recommended.


Setup
=====

Step 1: Create an Anthropic API key
-----------------------------------

#. Sign in to the `Anthropic Console <https://console.anthropic.com/>`_.
#. Go to **Settings → API Keys → Create Key**.
#. Give the key a descriptive name (for example ``smarter-napl-prod``) and copy
   the value immediately. It is shown only once.

.. danger::

   Never commit an API key to version control. Keep it in ``.env`` only, and
   make sure ``.env`` is listed in ``.gitignore``.

Step 2: Give the key to Smarter
-------------------------------

Add the key to the ``.env`` file at the root of your Smarter deployment:

.. code-block:: bash

   SMARTER_ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx

Restart the application so the new credential is loaded:

.. code-block:: bash

   make restart


Concept Overview
================

**Built-in versus additional providers.** OpenAI, GoogleAI and MetaAI are
registered automatically at deployment time; they only need their
``SMARTER_*_API_KEY`` variable. Anthropic is an *additional* provider, so it
needs **both** the API key (Step 2) **and** a Provider manifest (below).

**Smarter API Manifests (SAM).** Every Smarter resource, whether a provider,
llmclient or plugin, is described by a YAML manifest that you apply with the
CLI. A Provider manifest has four top-level keys:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Key
     - Purpose
   * - ``apiVersion``
     - Always ``smarter.sh/v1``.
   * - ``kind``
     - Always ``Provider`` for this resource.
   * - ``metadata``
     - ``name``, ``description`` and ``version`` of this resource.
   * - ``spec``
     - The provider configuration: which backend (``provider.name``) and which
       model (``provider.model``).

**One manifest per model.** A manifest maps to one provider/model pair. To
offer two Claude models you apply two manifests.

**Verification.** When a manifest is applied, Smarter registers the provider
and then runs asynchronous verification checks: it calls the provider's API,
confirms the model is reachable and compatible with Smarter resources, and
marks the provider active. Checks are re-run periodically so compatibility
does not silently drift.


Step-by-Step
============

Step 3: Generate a reference manifest
-------------------------------------

.. code-block:: bash

   smarter manifest provider

This prints a valid example manifest. Compare your own files against it if
Smarter rejects them.

Step 4: Write the manifests
---------------------------

Create ``anthropic-opus.yaml`` (higher capability, suited to complex
reasoning):

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-opus
     description: Anthropic Claude Opus for NAPL, high-capability model
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-opus-4-5

Create ``anthropic-sonnet.yaml`` (faster and more cost-efficient):

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-sonnet
     description: Anthropic Claude Sonnet for NAPL, balanced speed and quality
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-sonnet-4-6

.. warning::

   Model identifiers are case-sensitive and must match Anthropic's published
   names exactly. Anthropic retires and adds models over time, so check the
   model list in the `Anthropic API documentation <https://docs.anthropic.com/>`_
   for the current identifiers before you apply.

Step 5: Apply the manifests
---------------------------

.. code-block:: bash

   smarter apply -f anthropic-opus.yaml
   smarter apply -f anthropic-sonnet.yaml

Smarter registers each provider and starts verification automatically.

Step 6: Confirm both providers are active
-----------------------------------------

.. code-block:: bash

   smarter describe provider anthropic-opus
   smarter describe provider anthropic-sonnet

Look for a ``status`` section showing that verification passed. If it shows
``pending``, wait about 30 seconds and run the command again; verification is
asynchronous.

You can also confirm in the web console: **Providers** in the left sidebar
should list both providers with active status.

.. tip::

   With both providers registered you can create two llmclients, one per model,
   and send the same prompt to each in the Workbench. This is a practical way
   to weigh cost against quality before choosing a default for the programming
   area.


Proof of Concept
================

Run the two ``describe`` commands again. Each output should end with a
``status`` block similar to this (timestamps will differ):

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-opus
     description: Anthropic Claude Opus for NAPL, high-capability model
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-opus-4-5
   status:
     verified: true
     active: true

``verified: true`` means Smarter made a live call to Anthropic's API and the
model is ready for use in llmclients and the Workbench.


Troubleshooting
===============

**Startup error: "API key not found"**
   ``SMARTER_ANTHROPIC_API_KEY`` is missing from ``.env``, misspelled, or the
   application was not restarted. Fix the variable and run ``make restart``.

**Provider status: "verification failed"**
   The API key is invalid or has been revoked. Create a new key in the
   Anthropic Console, update ``.env``, then run ``make restart``.

**Apply error: "Model not found"**
   The ``model`` value does not match Anthropic's published identifier
   (identifiers are case-sensitive), or the model has been retired. Check the
   current list and correct the manifest.

**Status stays "pending"**
   Verification is asynchronous. Wait a minute and describe the provider again.
   If it never completes, ask your platform administrator to check the server
   logs (the web console includes a live log viewer).

**Manifest validation errors**
   YAML indentation is the usual cause. Compare your file against the output
   of ``smarter manifest provider``.


.. seealso::

   - `Smarter Provider <https://docs.smarter.sh/smarter-resources/smarter-provider.html>`_
   - `Smarter API Manifests (SAM) for Provider <https://docs.smarter.sh/smarter-resources/provider/manifest.html>`_
   - `Smarter CLI <https://docs.smarter.sh/smarter-framework/smarter-cli.html>`_
   - `Anthropic API documentation <https://docs.anthropic.com/>`_

.. note::

   **AI Usage Disclaimer**
   This documentation was created as part of coursework. Generative AI tools (including Claude Code / LLM assistance) were utilized to assist in drafting, structuring, and refining these technical materials in accordance with course guidelines. All content has been reviewed, verified, and edited for technical accuracy.

   