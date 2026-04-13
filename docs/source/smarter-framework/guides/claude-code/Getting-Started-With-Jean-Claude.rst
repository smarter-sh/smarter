Smarter & Claude is Jean-Claude Van Damme - Getting Started Guide
====================================================================

.. contents:: Table of Contents
   :local:
   :depth: 3

Goal
----

Use the Smarter CLI to register Anthropic as an LLM provider, apply a
provider manifest, verify connectivity, and send your first prompt to a
Claude-backed chatbot — all in under fifteen minutes.

Prerequisites
-------------

- An active Smarter account.
- Smarter v0.11.0 or later, running and accessible.
- Comfort working in a terminal (Bash, Zsh, or PowerShell).
- Basic understanding of YAML syntax and REST APIs.

.. note::

   This tutorial assumes you can already log in to the Smarter web console.
   If you cannot, contact your organization's Smarter administrator.

- An active Anthropic account with API access and a valid API key.

Setup
-----

Step 1: Install the Smarter CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Follow the installation instructions in :doc:`/smarter-framework/smarter-cli`
to download the binary for your operating system and add it to your ``PATH``.

Confirm the installation:

.. code-block:: bash

   smarter version

You should see output similar to ``smarter v0.11.x (build ...)``.

Step 2: Create and Set a Smarter API Key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Log in to the Smarter web console.
2. Click your profile icon (top-right) and select **API Keys**.
3. Click **Create API Key**, give it a descriptive name (e.g.
   ``my-admin-key``), and copy the value immediately — it will not be
   shown again.

Export the key so subsequent commands pick it up automatically:

.. code-block:: bash

   export SMARTER_API_KEY=your-api-key-here

Step 3: Configure the CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   smarter configure

When prompted, provide the target environment (e.g. ``prod``, ``alpha``) and
the API key from Step 2. Run a quick health check to make sure everything is
connected:

.. code-block:: bash

   smarter status

A successful response confirms the platform is reachable and your credentials
are valid.

Step 4: Obtain an Anthropic API Key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Sign in at `https://console.anthropic.com/ <https://console.anthropic.com/>`_.
2. Navigate to **Settings → API Keys → Create Key**.
3. Give the key a descriptive name (e.g. ``smarter-prod``) and copy it
   immediately — Anthropic will not display it again.

For full details on API key management, authentication, and rate limits, see
the `Claude API documentation <https://platform.claude.com/docs/en/home>`_.

.. danger::

   Never commit API keys to version control. Store them only in environment
   variables or a secrets manager.

Step 5: Add the Anthropic Key to Smarter's Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open the ``.env`` file at the root of your Smarter deployment and add:

.. code-block:: bash

   SMARTER_ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Restart the application so the new credential is loaded:

.. code-block:: bash

   make restart

Concept Overview
----------------

Smarter manages every resource — providers, chatbots, plugins — through
declarative YAML manifests applied via the CLI. This pattern is deliberately
modeled on Kubernetes. These files are called **SAM** (Smarter API Manifests).

Provider
~~~~~~~~

A **Provider** represents an external LLM backend (e.g. Anthropic, OpenAI,
GoogleAI). Smarter uses the provider definition to know which API to call,
which credentials to use, and which model to target.

Provider Manifest
~~~~~~~~~~~~~~~~~

A Provider manifest has four top-level sections:

- ``apiVersion``: Always ``smarter.sh/v1``.
- ``kind``: Set to ``Provider``.
- ``metadata``: Name, description, and version of this resource.
- ``spec``: The provider configuration — which backend and which model.

When you apply a manifest, Smarter registers the provider and immediately runs
**verification**: it calls the provider's API, confirms the model is reachable,
and marks the provider active.

.. note::

   Built-in providers (OpenAI, GoogleAI, MetaAI) are registered automatically
   during deployment and only require their ``SMARTER_*`` environment variable.
   Anthropic is an **additional provider** and requires both the environment
   variable *and* a manifest.

Chatbot
~~~~~~~

A **Chatbot** is a named resource that bundles a provider, a model, a system
prompt, and optional data plugins. End users interact with chatbots, not
providers directly.

Provider vs. Model Identifiers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Each manifest registers **one model** under a provider backend. To offer
multiple Claude models (e.g. Opus and Sonnet), create one manifest per model.
Model identifiers are case-sensitive and must match the strings published by
Anthropic exactly.

.. list-table::
   :header-rows: 1
   :widths: 30 40 30

   * - Manifest Name
     - Model Identifier
     - Best For
   * - ``anthropic-opus``
     - ``claude-opus-4-5``
     - Complex reasoning, code generation
   * - ``anthropic-sonnet``
     - ``claude-sonnet-4-6``
     - Balanced speed and quality

For the full list of available Claude models and their capabilities, see the
`Claude API documentation <https://platform.claude.com/docs/en/home>`_.

Step-by-Step: Create and Apply Provider Manifests
-------------------------------------------------

Step 6: Generate a Starting Template
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   smarter manifest provider

This prints a valid example manifest to stdout. Use it as a reference while
authoring your own files.

Step 7: Write the Provider Manifests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create one manifest per model. The example below registers both Claude Opus
and Claude Sonnet so you can compare their responses side-by-side in the
Workbench.

``anthropic-opus.yaml`` — higher capability, best for complex reasoning:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-opus
     description: Anthropic Claude Opus 4 — high-capability model
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-opus-4-5

``anthropic-sonnet.yaml`` — faster and more cost-efficient:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-sonnet
     description: Anthropic Claude Sonnet 4 — balanced speed and quality
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-sonnet-4-6

.. note::

   Model identifiers are case-sensitive and must match the provider's published
   names exactly. For the full ``spec`` field reference, see
   :doc:`/smarter-resources/provider/sam`.

Step 8: Apply the Manifests
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   smarter apply -f anthropic-opus.yaml
   smarter apply -f anthropic-sonnet.yaml

Smarter registers each provider and begins verification checks automatically.

Step 9: Confirm Both Providers are Active
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   smarter describe provider anthropic-opus
   smarter describe provider anthropic-sonnet

Look for a ``status`` section in each output showing that verification has
passed. If it shows ``pending``, wait 30 seconds and run the command again —
verification is asynchronous.

You can also confirm in the web console: **Providers** in the left sidebar
should list both ``anthropic-opus`` and ``anthropic-sonnet`` with active
status.

Step 10: Send Your First Prompt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List available chatbots to find one configured with an Anthropic provider:

.. code-block:: bash

   smarter get chatbots

Start an interactive session:

.. code-block:: bash

   smarter chat <chatbot-name>

Type a prompt and press Enter. For example:

.. code-block:: text

   Write a Python function that validates an email address using a regex pattern.
   Include a Sphinx-compatible docstring.

Expected response (approximate):

.. code-block:: python

   import re


   def validate_email(address: str) -> bool:
       """Validate an email address against a standard pattern.

       :param address: The email address string to validate.
       :type address: str
       :returns: ``True`` if the address matches the pattern, ``False`` otherwise.
       :rtype: bool

       :Example:

       >>> validate_email("user@example.com")
       True
       >>> validate_email("not-an-email")
       False
       """
       pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
       return bool(re.match(pattern, address))

Proof of Concept
----------------

Run the following sequence end to end to verify your setup is complete:

.. code-block:: bash

   smarter status                              # platform is reachable
   smarter get providers                       # anthropic-opus and anthropic-sonnet listed
   smarter describe provider anthropic-opus    # verified: true, active: true
   smarter describe provider anthropic-sonnet  # verified: true, active: true
   smarter chat <chatbot-name>

Expected ``describe`` output for each provider:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-opus
     description: Anthropic Claude Opus 4 — high-capability model
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-opus-4-5
   status:
     verified: true
     active: true
     last_verified: "2026-04-06T00:00:00Z"

Both providers showing ``verified: true`` and ``active: true`` confirms that
Smarter has a live connection to the Anthropic API and both models are ready
for use in chatbots and the Workbench.

.. tip::

   With both providers registered, create two chatbots — one backed by Opus,
   one by Sonnet — and compare their responses to the same prompt in the
   Workbench. This is a practical way to evaluate cost vs. quality trade-offs
   before committing to a model for production.

Troubleshooting
---------------

Startup error: "API key not found"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``SMARTER_ANTHROPIC_API_KEY`` variable is missing from ``.env`` or the
application has not been restarted. Double-check the variable name (it is
case-sensitive) and run ``make restart``.

Provider status: "verification failed"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The API key is invalid, expired, or has been revoked. Generate a new key at
`console.anthropic.com <https://console.anthropic.com/>`_ and update ``.env``.
See the `Claude API documentation <https://platform.claude.com/docs/en/home>`_
for guidance on key rotation.

Apply error: "Model not found"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``model`` value in your manifest does not match the provider's published
identifier. Model identifiers are case-sensitive. Run
``smarter manifest provider`` to compare your file against a known-good
template, and consult the
`Claude API documentation <https://platform.claude.com/docs/en/home>`_ for
current model names.

Manifest validation errors
~~~~~~~~~~~~~~~~~~~~~~~~~~

YAML indentation is almost always the cause. Run ``smarter manifest provider``
to view a valid template and compare it against your file. Install the
`Smarter YAML extension <https://marketplace.visualstudio.com/items?itemName=querium.smarter-manifest>`_
in VS Code for autocomplete and live validation.

"Not authenticated" when using the CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run ``smarter configure`` and re-enter your Smarter API key. You can also pass
it inline with ``--api_key``.

Slow or timed-out responses
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run ``smarter status``. If the platform is healthy, the delay is on
Anthropic's side — wait a minute and retry. For persistent issues, check the
`Claude API status page <https://status.anthropic.com/>`_.

.. seealso::

   - :doc:`/smarter-framework/smarter-cli`
   - :doc:`/smarter-platform/api-keys`
   - :doc:`/smarter-resources/smarter-provider`
   - :doc:`/smarter-resources/provider/sam`
   - :doc:`/smarter-resources/provider/api`
   - :doc:`/external-links/swagger`
   - `Claude API Documentation <https://platform.claude.com/docs/en/home>`_
   - `Anthropic Console <https://console.anthropic.com/>`_
