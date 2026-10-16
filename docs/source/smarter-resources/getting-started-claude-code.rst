Getting Started: Add Anthropic (Claude) as an LLM Provider in Smarter
=====================================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

Goal
----

We will register **Anthropic** as an LLM provider in Smarter, using a Claude model suited to programming work, and verify that Smarter can reach it.

By the end you will have one ``Provider`` manifest applied and reporting ``verified: true``.

Prerequisites
-------------

You should already be comfortable with:

- A terminal (Bash, Zsh, or PowerShell) and environment variables
- Reading and writing YAML
- API-key handling: keys are secrets and never go into version control

Setup
-----

You need the following before starting:

1. **An Anthropic API key.** In `console.anthropic.com <https://console.anthropic.com/>`_ go to **Settings → API Keys → Create Key**. Copy the value immediately; it is shown only once.
2. **The Smarter CLI**, installed and configured. See :doc:`Smarter CLI <../smarter-framework/smarter-cli>`.

   .. code-block:: bash

      smarter version
      smarter configure
      smarter status

3. **Write access to your Smarter deployment’s** ``.env`` **file**, because the Anthropic key is supplied as a platform environment variable. If you do not have it, ask your Smarter administrator.
4. **Outbound HTTPS** from Smarter to ``api.anthropic.com:443``.

.. danger::

   Never commit API keys to version control. If a key leaks, revoke it in the Anthropic console and issue a new one.


Concept Overview
----------------

**Provider**
   An external LLM backend. Smarter uses the Provider to decide which API to call and which model to target.


**Claude Code and Claude models**
   Anthropic is the *provider*. Claude is the *model family*, and each manifest registers exactly one model, for example ``claude-sonnet-4-6``. Claude Code is Anthropic’s coding tool, and it runs on these same models.


**Manifest (SAM)**
   Smarter resources are declared in YAML and applied with the CLI, in the same style as Kubernetes. A Provider manifest has four sections:

   - ``apiVersion``: always ``smarter.sh/v1``
   - ``kind``: ``Provider``
   - ``metadata``: name, description, version
   - ``spec``: which backend and which model


**Verification**
   After you apply a manifest, Smarter calls the provider’s API, confirms the model is reachable, and marks the provider active. This runs asynchronously.


.. note::

   OpenAI, GoogleAI, and MetaAI are built in and need only an environment variable. Anthropic is an **additional provider**, so it needs the environment variable *and* a manifest.


Step-by-Step
------------

Step 1: Add the API key to Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add this line to the ``.env`` file at the root of your Smarter deployment:

.. code-block:: bash

   SMARTER_ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx

Restart so the credential is loaded:

.. code-block:: bash

   make restart

Step 2: Write the Provider manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Save as ``anthropic-sonnet.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-sonnet
     description: Anthropic Claude Sonnet for programming work
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-sonnet-4-6

.. tip::

   ``smarter manifest provider`` prints a valid template. For every ``spec`` field, see :doc:`Smarter API Manifests (SAM) <provider/manifest>`.


.. note::

   Model identifiers are case-sensitive and must match Anthropic’s published names exactly.


Step 3: Apply the manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   smarter apply -f anthropic-sonnet.yaml

Step 4: Check verification
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   smarter describe provider anthropic-sonnet

If ``status`` shows ``pending``, wait 30 seconds and run it again.

Proof of Concept
----------------

``smarter describe provider anthropic-sonnet`` returns a ``status`` block with ``verified: true`` and ``active: true``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-sonnet
     description: Anthropic Claude Sonnet for programming work
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-sonnet-4-6
   status:
     verified: true
     active: true

The provider also appears under **Providers** in the web console with active status.

Troubleshooting
---------------

**Startup error: “API key not found”**
   ``SMARTER_ANTHROPIC_API_KEY`` is missing from ``.env``, or the application was not restarted. Add it and run ``make restart``.


**Status: “verification failed”**
   The key is invalid, revoked, or blocked by network egress rules. Create a new key, update ``.env``, restart, and confirm ``api.anthropic.com:443`` is reachable.


**Apply error: “Model not found”**
   ``spec.provider.model`` does not match a model identifier Anthropic publishes. Check the spelling and case.


**Manifest validation errors**
   Usually YAML indentation. Compare your file with the output of ``smarter manifest provider``.


**Status stays “pending”**
   Verification is asynchronous. Wait 30 seconds and run ``describe`` again.


.. seealso::

   - :doc:`How-To: Adding an LLM Provider to Smarter <../smarter-platform/adding-an-llm-provider>`
   - :doc:`Smarter Provider <smarter-provider>`
   - `Anthropic API documentation <https://docs.anthropic.com/>`_
