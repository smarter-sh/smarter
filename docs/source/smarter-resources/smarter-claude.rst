Smarter Claude: Getting Started 
===============================

Goal
----
We will use Claude Code with Smarter to explore an existing software project, identify a function that can be tested independently, and add a unit test without changing the application's existing implementation.

Prerequisites
-------------

.. admonition:: You should have:

   An existing Smarter account and access to the approved environment.

   The Smarter CLI installed and configured.

   Git installed.

   An Anthropic API credential managed through your organization's approved secret-management system.
   
   Familiarity with YAML, command-line tools, and unit testing.

Setup
----

Register Anthropic as a Smarter provider before configuring Claude Code.

Step 1: Verify the CLI
======================

.. code-block:: console

   smarter version
   git --version

Confirm that the Smarter CLI targets the correct environment.

Step 2: Create the provider manifest
====================================

Generate a provider template:

.. code-block:: console

   smarter manifest provider

Use the generated template to create anthropic-provider.yaml. Configure the provider using the field names and credential references supported by your deployment.

Example configuration:

.. code-block:: yaml
 
   Create a file named ``anthropic-provider.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic_provider
     description: Anthropic provider for Claude models
     version: 1.0.0
   spec:
     provider:
       name: Anthropic
       description: Anthropic API provider
       base_url: https://api.anthropic.com/v1
       api_key: anthropic_api_key
       connectivity_test_path: /models

.. warning::
   Never commit API keys or other secrets to Git.

Step 3: Apply and verify the provider
=====================================

Apply the manifest and inspect the resulting resource:

.. code-block:: console

   smarter apply -f anthropic-provider.yaml
   smarter describe provider anthropicprovider
   smarter get llmclients

If a compatible LLMClient exists, inspect its configuration:

.. code-block:: console

   smarter describe llmclient <llmclient-name>

Replace ``<llmclient-name>`` with the actual resource name.

.. note::

   Registering a Provider does not automatically create an LLMClient or guarantee Claude Code integration. Follow your deployment's instructions to configure a compatible client, endpoint, authentication, and model.

Step 4: Verify Claude Code
==========================

Configure Claude Code using the supported Smarter integration instructions, then run:

.. code-block:: console
   claude --version

Confirm that Claude Code starts and can access the intended model through the configured integration.

Concept Overview
================

The integration involves three main components:


   Provider: Defines the upstream Anthropic service and its connection settings.

   LLMClient: Connects a Smarter client configuration to a provider and model.

   Claude Code: Uses an LLM to explore code, propose changes, and assist with testing.

The intended request flow is:

.. code-block:: text

   Developer | v Claude Code | v Supported Smarter integration | v LLMClient and Provider | v Anthropic Claude

The actual integration depends on the capabilities enabled in your Smarter deployment.

Step-by-Step: Add a Unit Test
-----------------------------

Step 1: Open the repository
===========================


.. code-block:: console

   cd /path/to/your/project
   git status

Review existing changes before proceeding.

Step 2: Explore the code
====================================

Ask Claude Code:

.. code-block:: text

   Identify this repository's main entry point, test framework, and test commands. Explain the relevant file paths. Do not modify any files.

Step 3: Create a unit test
====================================

Ask Claude Code to test an existing function:

.. code-block:: text

   Find an existing function that can be tested independently.

   Add a unit test for its existing behavior.

   Do not modify the function implementation.

   Follow the project's testing conventions and run the   relevant test. Explain the changes and results.

Review the proposed changes before accepting them.

Step 4: Inspect and test the changes
====================================

.. code-block:: console

   git status 
   git diff --check 
   git diff

Inspect untracked test files separately. Run the project's test command. For a Python project using pytest, for example:

.. code-block:: console

   pytest path/to/test_file.py

Verify that the test passes, the original implementation remains unchanged, and no unrelated files were modified.

Proof of Concept
----------------


   The tutorial is complete when you can demonstrate that:

   The Anthropic Provider is registered and its configuration is valid.

   A compatible LLMClient and working Claude Code integration are available.

   Claude Code has created a focused unit test for an existing function.

   The relevant test passes.

   The Git diff confirms that the original implementation is unchanged and no credentials or unrelated changes were introduced.

Troubleshooting
---------------
.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Problem
     - Resolution
   * - Manifest rejected
     - Check YAML indentation, required fields, and the generated
       provider template.
   * - Provider connectivity fails
     - Verify endpoint reachability, credential configuration,
       and provider status.
   * - No compatible LLMClient
     - Ask your Smarter administrator to confirm client support
       and permissions.
   * - Claude Code cannot connect
     - Verify the supported endpoint, authentication, model
       configuration, and integration availability.
   * - Tests fail or unexpected files change
     - Review test output, ``git status``, and ``git diff``.
       Correct unintended changes and rerun the tests.

Never expose credentials or bypass approved authentication while troubleshooting.

Technical Reference
-------------------

Claude Code documentation <https://docs.anthropic.com/en/docs/claude-code/overview>_