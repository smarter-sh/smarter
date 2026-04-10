Getting Started with Claude Code as a Coding Assistant
============================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

Goal
----

We will use Claude Code with Smarter to register an Anthropic provider, configure Claude models, and verify an end-to-end coding assistant workflow.
This guide is written for developers who already have Smarter accounts and deployment access, and want a repeatable on-ramp for Claude-powered code generation and code reasoning.

Prerequisites
-------------

- A working Smarter deployment accessible from your network.
- A Smarter administrator account with CLI access and permission to apply manifests.
- The Smarter CLI installed and authenticated with your deployment.
- Access to the Anthropic Console and a valid Anthropic API key.
- Familiarity with YAML, shell commands, and environment variable based configuration.
- Basic knowledge of provider/model abstractions in Smarter and how Smarter uses manifests.

.. note::

   This guide assumes you already know how to log in to Smarter and have an account provisioned.
   It does not cover account creation or general Smarter navigation.

Setup
-----

Before you begin, make sure you are ready to complete the Claude Code integration:

- A working Smarter deployment is running and accessible.
- You have Smarter administrator access and CLI credentials.
- The Smarter CLI is installed and authenticated with your deployment.
- You can edit your deployment's ``.env`` file and restart the running service.
- You have access to the Anthropic Console and can generate an API key.
- You are comfortable authoring YAML provider manifests.

If you want a deeper reference for provider manifests, see
:doc:`/smarter-platform/adding-an-llm-provider`.

Step-by-Step
------------

Step 1: Obtain an Anthropic API key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Open the Anthropic Console at `https://console.anthropic.com/ <https://console.anthropic.com/>`_.
2. Create a new API key for the Smarter integration.
3. Copy the key immediately; Anthropic shows it only once.

.. figure:: /_static/api-key-claude.png
   :alt: Anthropic API key creation screenshot
   :align: center

   Create and copy the Anthropic API key.

Step 2: Add the key to Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open the Smarter deployment ``.env`` file and add the Anthropic key:

.. code-block:: bash

   SMARTER_ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

If you use a deployment helper, add the value there instead.

.. caution::

   Never commit the Anthropic API key or any secret directly to source control.

Then restart Smarter so the environment variable is loaded. For local Docker-based deployments, use ``docker compose restart``.

.. code-block:: bash

   docker compose restart

Step 3: Create Claude provider manifests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Smarter uses YAML manifests to register resources. For Claude Code you should register each Anthropic model you want to use.
The manifest format is the same for any additional provider.

Example: ``anthropic-opus.yaml``

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-opus
     description: Anthropic Claude Opus 4 — high-capability coding assistant
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-opus-4-5

Example: ``anthropic-sonnet.yaml``

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-sonnet
     description: Anthropic Claude Sonnet 4 — balanced coding assistance
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-sonnet-4-6

.. note::

   The ``model`` identifier must match Anthropic's published model names exactly.
   Model names are case-sensitive.

Step 4: Apply the manifests
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Execute the Smarter CLI to register the providers:

.. code-block:: bash

   smarter apply -f anthropic-opus.yaml
   smarter apply -f anthropic-sonnet.yaml

Smarter validates the manifests, registers the providers, and performs live verification checks against Anthropic.

Step 5: Verify provider registration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Confirm each provider is active:

.. code-block:: bash

   smarter describe provider anthropic-opus
   smarter describe provider anthropic-sonnet

Expected result includes a ``status`` section such as:

.. code-block:: yaml

   status:
     verified: true
     active: true
     last_verified: "2026-03-31T00:00:00Z"

If verification is pending, wait 30 seconds and re-run the command.

Step 6: Use Claude in Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the provider is active, open the Smarter Workbench and select your Anthropic provider.
The Workbench is the recommended place to interactively evaluate Claude Code as a coding assistant.

Prompt the model with a coding task.

.. raw:: html

   <div style="text-align: center;">
     <video src="https://cdn.smarter.sh/videos/read-the-docs2.mp4"
            autoplay loop muted playsinline
            style="width: 100%; height: auto; display: block; margin: 0; border-radius: 0;">
       Sorry, your browser doesn't support embedded videos.
     </video>
     <div style="font-size: 0.95em; color: #666; margin-top: 0.5em;">
       <em>Smarter Prompt Engineering Workbench Demo</em>
     </div>
   </div>
   <br/>


Step 7: Installation Verification checklist
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- ``SMARTER_ANTHROPIC_API_KEY`` exists in ``.env``.
- ``smarter apply`` exits without manifest errors.
- ``smarter describe provider anthropic-opus`` returns ``verified: true``.
- The provider is visible in the Smarter console.
- A Workbench session can generate a valid code snippet from a prompt.

Concept Overview
----------------
Smarter as the orchestration layer and Anthropic Claude as the computation engine. Smarter sends standardized requests, then routes results into chatbots, Workbench sessions, and downstream pipelines.

Smarter decomposes AI integration into two key concepts:

- ``Provider``: the external service that hosts the model and handles authentication.
- ``Provider model``: the specific model identity and capabilities offered by that service.

A provider manifest connects these concepts in Smarter using a standard resource model.
It is intentionally similar to Kubernetes manifests so the workflow is familiar to engineers.

Key runtime behavior
~~~~~~~~~~~~~~~~~~~~~

- Smarter reads the Anthropic API key from ``.env``.
- The provider manifest declares which Anthropic model to use.
- Smarter performs a verification request during registration.
- After verification, the provider appears as available in the console and CLI.


Proof of Concept
----------------

The expected result of this walkthrough is a Claude Code provider that is registered, verified, and usable from the Smarter Workbench.

Concrete success criteria:

- The Anthropic provider manifest is applied without manifest or validation errors.
- ``smarter describe provider anthropic-opus`` returns ``verified: true`` and ``active: true``.
- The provider is visible in the Smarter console under **Providers**.
- The provider can be selected in the Workbench and responds to a developer prompt.
- A sample coding prompt returns a valid code snippet, not an error message.

Example CLI verification output:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-opus
     description: Anthropic Claude Opus 4 — high-capability coding assistant
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-opus-4-5
   status:
     verified: true
     active: true
     last_verified: "2026-03-31T00:00:00Z"

Example Workbench outcome:

- Prompt: ``Write a Python function that normalizes user profile data``
- Result: a complete Python function with comments and a small validation example
- No authentication failures, no model-not-found errors, and no invalid provider status

If you can complete the steps above, the Claude Code integration is working and the guide's objective has been met.

Troubleshooting
---------------

**Problem: Provider does not appear in Smarter**

- Confirm the manifest was applied successfully.
- Verify that the provider name in YAML is ``anthropic`` and the model string is correct.
- Check ``smarter describe provider <name>`` for details.

**Problem: Verification failed**

- Verify ``SMARTER_ANTHROPIC_API_KEY`` is present in ``.env``.
- Restart Smarter after changing ``.env`` using your deployment workflow. The repository does not include a ``make restart`` target; for local Docker deployments use ``docker compose restart``.
- Confirm the API key is active and has not been revoked.
- Ensure network access can reach ``https://api.anthropic.com``.

**Problem: Manifest validation errors**

- Use ``smarter manifest provider`` as a template.
- Ensure YAML indentation is correct.
- Do not use tabs.

**Problem: Workbench prompts do not produce code**

- Confirm the chosen provider is active in the console.
- Use a more explicit prompt that frames the request as code generation.
- Compare Opus and Sonnet models for quality vs latency.

**Problem: Environment values not loading**

- Make sure the deployment is restarted after updating ``.env``.
- If Smarter runs in containers, inspect the container environment and restart the service.
- For containerized setups, use ``docker compose restart`` or your deployment-specific restart command.

.. seealso::

   - :doc:`/smarter-platform/adding-an-llm-provider`
   - :doc:`/smarter-framework/guides/claude-code/claude-code-with-smarter`
   - :doc:`/external-links/claude-reference`
