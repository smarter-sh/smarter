=============================================
Getting Started: Using Claude Code with Smarter
=============================================

Goal
====

In this tutorial, we will add **Anthropic** as an LLM provider in **Smarter**, register the **Claude Code** model family, and verify that Claude models are available for developers through the Smarter platform. Once completed, programmers will be able to use Claude-powered services through Smarter-managed resources. 【1-3f0edf】

Prerequisites
=============

This tutorial assumes you already have:

* Strong familiarity with YAML configuration files.
* Basic knowledge of API keys and environment variable management.
* Access to a deployed Smarter environment.
* An administrator-level Smarter account with permission to manage providers.
* The Smarter CLI installed and authenticated.
* Access to an Anthropic account capable of generating API keys. 【1-3f0edf】

Setup
=====

Before adding Anthropic to Smarter, ensure the following components are available:

1. A running Smarter deployment (v0.11.0 or later).
2. A working Smarter CLI installation.
3. Access to the Smarter deployment's ``.env`` file.
4. An Anthropic API key generated from:

   ::

      https://console.anthropic.com

5. A text editor that supports YAML syntax validation. Visual Studio Code with the Smarter YAML extension is recommended. 【1-3f0edf】

Concept Overview
================

Smarter manages infrastructure resources through **SAM (Smarter API Manifests)**. SAM files are declarative YAML documents similar in concept to Kubernetes manifests. A manifest describes the desired state of a resource and Smarter applies that state automatically. 【1-3f0edf】

When adding an LLM provider, Smarter requires two categories of information:

Provider Credential Data
------------------------

The provider API credential must be stored in the platform environment.

For Anthropic:

::

   SMARTER_ANTHROPIC_API_KEY=<your-api-key>

This credential allows Smarter to authenticate against Anthropic services. 【1-3f0edf】

Provider Manifest Data
----------------------

Every Provider manifest contains four required sections:

* ``apiVersion``
* ``kind``
* ``metadata``
* ``spec``

The specific data points required by Smarter are:

================== ==========================================
Field              Purpose
================== ==========================================
apiVersion         Manifest API version
kind               Resource type (Provider)
metadata.name      Unique provider identifier
metadata.description Human-readable description
metadata.version   Resource version
spec.provider.name Backend provider name
spec.model         Target model identifier
================== ==========================================

Smarter uses this information to register the provider and verify connectivity to the model endpoint. Successful verification marks the provider as active and available platform-wide. 【1-3f0edf】

Step-by-Step
============

Step 1: Create an Anthropic API Key
-----------------------------------

1. Sign in to Anthropic.

2. Navigate to:

   ::

      Settings -> API Keys

3. Create a new API key.

4. Copy the key immediately and store it securely.

Never commit API keys to source control. 【1-3f0edf】

Step 2: Configure Smarter Environment Variables
------------------------------------------------

Open the Smarter deployment's ``.env`` file and add:

::

   SMARTER_ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx

Restart Smarter after updating the environment variable:

::

   make restart

This allows Smarter to authenticate with Anthropic. 【1-3f0edf】

Step 3: Generate a Provider Template
------------------------------------

Use the Smarter CLI:

::

   smarter manifest provider

This command generates a sample Provider manifest and helps validate the expected structure. 【1-3f0edf】

Step 4: Create the Anthropic Provider Manifest
----------------------------------------------

Create a file named:

::

   anthropic-claude-code.yaml

Contents:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider

   metadata:
     name: anthropic-claude-code
     description: Anthropic Claude Code provider
     version: 1.0.0

   spec:
     provider:
       name: anthropic
     model: claude-sonnet-4-6

Required information supplied in this manifest:

* Provider name: ``anthropic``
* Model identifier: ``claude-sonnet-4-6``
* Unique manifest name
* Description
* Version number 【1-3f0edf】

Step 5: Apply the Manifest
--------------------------

Register the provider:

::

   smarter apply -f anthropic-claude-code.yaml

Smarter will create the resource and begin provider validation. 【1-3f0edf】

Step 6: Verify Registration
---------------------------

List configured providers:

::

   smarter get providers

Expected output should show the newly registered Anthropic provider in an active or verified state. Smarter automatically performs verification checks against the provider API during registration. 【1-3f0edf】

Step 7: Configure Claude Code
-----------------------------

After the provider is registered successfully:

1. Open your Claude Code development environment.
2. Select the Smarter-managed Anthropic provider.
3. Choose the registered Claude model.
4. Begin development using the centrally managed provider instead of local credentials.

Because credentials are stored within Smarter, developers do not need direct access to the Anthropic API key. 【1-3f0edf】

Proof of Concept
================

A successful implementation should produce the following results:

* Anthropic appears in the list of registered providers.
* The provider status is verified or active.
* The model ``claude-sonnet-4-6`` is available to Smarter clients.
* Claude Code can submit prompts through the Smarter platform.
* Developers can use Claude functionality without handling API credentials directly. 【1-3f0edf】【2-6ebab5】

Example verification command:

::

   smarter get providers

Example expected result:

::

   NAME                    PROVIDER     MODEL
   anthropic-claude-code   anthropic    claude-sonnet-4-6

Troubleshooting
===============

Provider Does Not Appear
------------------------

Verify the manifest was applied successfully:

::

   smarter get providers

Then reapply:

::

   smarter apply -f anthropic-claude-code.yaml

Invalid API Key
---------------

Confirm that:

* ``SMARTER_ANTHROPIC_API_KEY`` exists in ``.env``
* The key begins with ``sk-ant-``
* The application was restarted after updating the value. 【1-3f0edf】

Model Verification Fails
------------------------

The model identifier must exactly match the provider's published model name.

For example:

::

   claude-sonnet-4-6

Model names are case-sensitive. 【1-3f0edf】

Permission Errors
-----------------

Ensure your account:

* Has administrator privileges within Smarter.
* Has permission to create Provider resources.
* Has access to execute ``smarter apply`` commands. 【1-3f0edf】

YAML Validation Errors
----------------------

Common causes include:

* Incorrect indentation.
* Missing ``apiVersion``.
* Missing ``kind``.
* Invalid ``metadata`` fields.
* Incorrect nesting under ``spec``.

Validate the YAML before applying the manifest. 【1-3f0edf】

Summary
=======

To onboard Anthropic in Smarter, you must supply:

1. An Anthropic API key through the ``SMARTER_ANTHROPIC_API_KEY`` environment variable.
2. A Provider SAM manifest containing:

   * ``apiVersion``
   * ``kind``
   * ``metadata.name``
   * ``metadata.description``
   * ``metadata.version``
   * ``spec.provider.name``
   * ``spec.model``

After applying the manifest and passing Smarter verification, Claude models become available across the platform, including developer tools such as Claude Code. 【1-3f0edf】