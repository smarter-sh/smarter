============================================
How-To: Add Anthropic and Claude to Smarter
============================================

.. image:: https://img.shields.io/badge/Anthropic-Claude%204-2563eb?style=flat-square&logo=anthropic&logoColor=white
   :target: https://www.anthropic.com
   :alt: Anthropic Claude 4

.. image:: https://img.shields.io/badge/GitHub-project--smarter-2ea44f?style=flat-square&logo=github&logoColor=white
   :target: https://github.com/smarter-sh
   :alt: GitHub

Goal
====
Configure Anthropic as an LLM (Large Language Model) provider so that Smarter can communicate with Claude models through the Anthropic API.

Prerequisites
=============

Before beginning this tutorial, ensure the following requirements are available:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Requirement
     - Purpose
   * - Smarter source code
     - Provides the project files you will configure.
   * - Git
     - Downloads and updates the source code.
   * - Docker Desktop and Docker Compose
     - Runs the application locally in containers, if the project uses Docker.
   * - Python
     - Supports local setup if required by the project.
   * - Anthropic account and API key
     - Authenticates requests to the Anthropic API.
   * - Terminal and text editor
     - Lets you run commands and edit configuration files.


Concept Overview
---------------------

The following diagram illustrates how Anthropic integrates with Smarter
and exposes Claude models to developers.


.. graphviz::

   digraph LLM_Workflow {
      graph [
         rankdir=TB,
         bgcolor="white",
         pad="0.25",
         nodesep="0.30",
         ranksep="0.40",
         splines=ortho
      ];

      node [
         shape=box,
         style="rounded,filled",
         fillcolor="#F3F5F7",
         color="#D5DCE3",
         penwidth=1.0,
         fontname="Arial",
         fontsize=11,
         fontcolor="#344454",
         margin="0.25,0.16",
         width=4.8
      ];

      edge [
         color="#8795A3",
         penwidth=1.2,
         arrowsize=0.7,
         arrowhead=vee
      ];

      Anthropic [
         label="Anthropic Console\nCreate an API key",
         fillcolor="#FFFFFF",
         color="#C8D2DC"
      ];

      Smarter [
         label="Secure Configuration\nMake the API key available to the application",
         fillcolor="#F1F4F7"
      ];

      ClaudeModel [
         label="Smarter Provider Configuration\nRegister Anthropic and select a supported model",
         fillcolor="#E9EEF3"
      ];

      ClaudeCode [
         label="Verification\nConfirm the application can use the provider",
         fillcolor="#FFFFFF",
         color="#C8D2DC"
      ];

      Anthropic -> Smarter;
      Smarter -> ClaudeModel;
      ClaudeModel -> ClaudeCode;
   }


Step-by-Step
============

Step 1: Obtain the Smarter source code
--------------------------------------
1. Open the project's public GitHub repository.
2. Clone the repository to your computer, or download its source code.
3. Open the project folder in your preferred editor.
4. Read the project's setup instructions and identify the required software versions.

.. note::

   A GitHub account is generally not required to clone a public repository.

Step 2: Set up Smarter locally
-----------------------------------
1. Install the tools required by the project, such as Git, Docker Desktop, or Python.
2. Follow the project's local setup procedure.
3. Start the application and confirm that it runs before changing the provider configuration.

**Expected result:** Smarter runs successfully in your local environment.

Step 3: Obtain an Anthropic API Key
------------------------------------

1. Open the `Anthropic Console <https://platform.claude.com/>`_.
2. Sign in or create an account.
3. Navigate to ``Settings → API keys``.
4. Create an API key and copy it.
5. Store it securely. Never commit the key to source control or expose it in application code.


Step 4: Configure the API Key
-----------------------------

1. Make the API key available to Smarter through its supported
   secret-management or environment-variable configuration.

2. For a local development environment, Anthropic's standard
   environment variable is:

   .. code-block:: bash

      ANTHROPIC_API_KEY=your-api-key

3. Use the format appropriate for your operating system and
   configuration file.

4. Do not commit the actual key to GitHub or include it directly
   in provider manifests.

**Expected Result** Smarter can access the credential without exposing it in source control.

.. caution::

   Never commit API keys to version control or share them in plain text.
   The key will be stored in the Smarter ``.env`` file on the server, which
   should be excluded from source control.


Step 5: Create a Provider Manifest
----------------------------------

Smarter uses YAML manifests to register provider resources. Create one
manifest for each Anthropic model you want to use.

Example 1: Claude Opus
^^^^^^^^^^^^^^^^^^^^^^

Create a file named ``anthropic-opus.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider

   metadata:
     name: anthropic-opus
     description: Anthropic Claude Opus - high-capability coding assistant
     version: 1.0.0

   spec:
     provider:
       name: anthropic
       model: claude-opus-4-5

Example 2: Claude Sonnet
^^^^^^^^^^^^^^^^^^^^^^^^

Create a file named ``anthropic-sonnet.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider

   metadata:
     name: anthropic-sonnet
     description: Anthropic Claude Sonnet - balanced coding assistance
     version: 1.0.0

   spec:
     provider:
       name: anthropic
       model: claude-sonnet-4-6

Validation
^^^^^^^^^^

Before applying the manifests, verify that:

.. rst-class:: check-list

* The YAML indentation and structure are valid.
* Each provider resource has a unique name.
* The provider name is ``anthropic``.
* The model identifier matches an available Anthropic model.
* Authentication is configured through the mechanism expected by the application.

.. note::

   * Model identifiers are case-sensitive and must match Anthropic's
     published identifiers.

   * Keep API credentials out of the manifest unless the platform
     explicitly requires a secure secret reference.

Step 6: Apply the Manifest
--------------------------

1. Apply the YAML manifest to register the provider with Smarter.
2. The Smarter GitHub repository documents the apply ``-f`` command pattern for deploying manifest files. 
3. Run the command from your terminal:

   .. code-block:: bash

      smarter apply -f anthropic-provider.yaml

**Expected result:** The manifest is accepted and the provider resource is created or updated.
If the command fails, check the YAML syntax, required fields, CLI authentication, and permissions.

.. note::
   Applying a manifest registers the resource; it does not necessarily prove that an end-to-end model request will succeed.

Step 7: Verify the Provider
---------------------------

Verify both the provider registration and its connectivity to Anthropic.

1. **Confirm registration**

   Use the supported ``CLI`` command or Smarter interface to locate
   ``anthropic-provider``.

2. **Inspect the provider status**

   Check the available resource details for:

   - Provider name and configuration
   - Successful validation or verification status, if provided
   - Authentication and connectivity errors

3. **Test an actual request**

   Send a small test prompt through the Smarter component that uses the
   provider. Confirm that the request succeeds and returns a response.

**Expected result:** The provider is registered, its configuration is valid, and a test request completes successfully.

.. important::
   The exact status fields and provider-inspection command must be confirmed against the CLI and source code version being used.


Step 8: Create the Anthropic Provider Configuration
---------------------------------------------------

1. Locate the application's provider configuration or manifest directory.
2. Review an existing provider configuration to understand the required
   structure.
3. Create a new configuration for Anthropic.
4. Specify the provider's required details, including:

   - Provider name
   - API endpoint
   - Authentication reference
   - Supported model

5. Validate the configuration against the schema expected by the installed
   version of Smarter.

Anthropic's API endpoint for message requests is:

.. code-block:: text

   https://api.anthropic.com

And the Messages API uses:

.. code-block:: text

   /v1/messages


.. important::

   The exact YAML fields and commands for registering a provider should be
   verified against the Smarter source code or an existing provider
   implementation. Do not assume that a generic YAML example will work in
   every deployment.

Step 9: Register the Provider
-----------------------------

1. Identify how the application loads provider configurations.
2. Add the Anthropic configuration using the project's supported
   registration or deployment process.
3. Restart or reload the relevant services if required.
4. Review application logs for configuration errors.

**Expected Result** Smarter recognizes the Anthropic provider configuration and loads it
successfully.

Step 10: Verify the Integration
-------------------------------

.. rst-class:: check-list

* The provider configuration passes validation.
* The API key is available to the application.
* The selected model is supported and accessible.
* Smarter can connect to Anthropic.
* A test request returns a successful response.
* Errors are logged without exposing API credentials.

For a successful end-to-end test, submit a request through Smarter rather than
testing the Anthropic API directly.

Proof of Concept
================

The proof of concept is considered complete when Smarter can successfully send
a request through the newly configured Anthropic provider and receive a
response from a supported Claude model.

Record the following information:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Item
     - Description
   * - Test Environment
     - Environment used during validation.
   * - Claude Model
     - Claude model selected for testing.
   * - Test Result
     - Successful or failed execution outcome.
   * - Issues Found
     - Any errors, warnings, or observations.

Expected Outcome
================

At the completion of this tutorial, Smarter should expose an Anthropic-backed
Claude model that can be used by programmers for Claude Code and other
Smarter-integrated development workflows.

Troubleshooting
===============

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Problem
     - What to Check
   * - Authentication failure
     - Confirm that the API key is valid and correctly configured.
   * - Provider configuration error
     - Check required fields, indentation, and schema validation.
   * - Connection failure
     - Verify network access and confirm the Anthropic API endpoint.
   * - Model unavailable
     - Confirm that the model identifier is valid and your account has access.
   * - Application does not recognize the provider
     - Review the provider registration mechanism and application logs.
   * - API request fails due to usage limits or billing
     - Review the Anthropic Console and account limits.

Final Recommendation
====================

Before finalizing your deployment, inspect the Smarter source repository and
confirm the following implementation-specific details:

1. Where provider configurations are stored.
2. How a new provider is registered.
3. How to select the provider and test requests through Smarter.

These details distinguish a general integration guide from a practical tutorial
that developers can follow successfully within a real Smarter deployment.
