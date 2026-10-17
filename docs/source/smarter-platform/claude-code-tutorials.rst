.. _claude-code-tutorials:

======================
Claude Code Tutorials
======================

.. contents:: Table of Contents
   :local:
   :depth: 3

How-To: Adding an LLM Provider
==============================

Goal
----

Register Anthropic as an LLM provider in Smarter so that Claude Code can
use an Anthropic model through the Smarter platform.

Prerequisites
-------------

Before you begin, make sure you have:

- Access to a Smarter account with permission to configure LLM providers.
- The Smarter CLI installed and configured.
- Access to an Anthropic account with permission to create API keys.
- Basic familiarity with YAML configuration files and command-line tools.

Setup
-----

The following walkthrough uses Anthropic as the example LLM provider.

Step 1: Get an Anthropic API Key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Sign in to the `Anthropic Console <https://console.anthropic.com/>`_.
2. Navigate to **Settings → API Keys** and create a new API key.
3. Copy the API key and keep it secure.

.. danger::

   Never commit API keys to version control.

Step 2: Store the Anthropic API Key in a Secret
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
       description: "Anthropic API key. Keep this value private."
       value: sk-ant-YOUR_API_KEY_HERE

Replace ``YOUR_API_KEY_HERE`` with your Anthropic API key.

Apply the Secret using the Smarter CLI:

.. code-block:: bash

   smarter apply -f anthropic-secret.yaml

.. warning::

   Never commit a manifest containing a real API key to version control.

Concept Overview
----------------

Smarter uses YAML manifests to define and manage resources such as LLM
providers. These files are called **SAM** (Smarter API Manifests).

For Anthropic, the configuration uses three resources:

- ``Secret`` stores the Anthropic API key.
- ``Provider`` defines the Anthropic API endpoint and references the Secret
  by name.
- ``ProviderModel`` registers a specific model, in this example
  ``claude-sonnet-4-6``, under the Anthropic provider.

Each SAM manifest identifies its resource with ``apiVersion``, ``kind``, and
``metadata``. The ``spec`` section contains the settings for that resource.
The Secret handles provider authentication, the Provider defines the backend,
and the ProviderModel makes a specific model available in Smarter.

Step-by-Step: Create and Apply the Provider and Model
------------------------------------------------------

Step 3: Create the Provider Manifest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a file named ``anthropic-provider.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: Anthropic
     description: >
       Anthropic PBC — maker of the Claude family of large language models.
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
     api_key: anthropic-api-key

Apply the Provider manifest:

.. code-block:: bash

   smarter apply -f anthropic-provider.yaml

After applying the manifest, verify the provider:

.. code-block:: bash

   smarter describe provider Anthropic

Step 4: Register the Claude Model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a file named ``anthropic-claude-code-model.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: ProviderModel
   metadata:
     name: claude-sonnet-4-6
     description: >
       Claude Sonnet 4.6 — the model used for coding tasks with Claude Code.
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

Apply the model manifest:

.. code-block:: bash

   smarter apply -f anthropic-claude-code-model.yaml

Step 5: Verify the Full Provider Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

List the registered providers:

.. code-block:: bash

   smarter get providers

Confirm that Anthropic appears in the list.

Inspect the provider configuration:

.. code-block:: bash

   smarter describe provider Anthropic -o yaml

Confirm that the provider status indicates successful verification:

.. code-block:: yaml

   status:
     is_active: true
     is_verified: true
     status: verified

List the models registered under Anthropic:

.. code-block:: bash

   smarter get providers Anthropic models

Confirm that ``claude-sonnet-4-6`` appears in the model list.

Proof of Concept
----------------

Confirm that the Anthropic provider is registered and verified:

.. code-block:: bash

   smarter describe provider Anthropic -o yaml

Confirm that the output indicates the provider is active and verified.

Confirm that the Claude model is registered:

.. code-block:: bash

   smarter get providers Anthropic models

The proof of concept is successful when the Anthropic provider is verified
and ``claude-sonnet-4-6`` appears in the registered model list.

Troubleshooting
---------------

**The provider is not verified**

Run the following command to inspect the provider configuration and status:

.. code-block:: bash

   smarter describe provider Anthropic -o yaml

Check that the Secret exists and that the API key is valid.

**The Claude model does not appear in the model list**

Run:

.. code-block:: bash

   smarter get providers Anthropic models

Verify that the ``ProviderModel`` manifest uses ``Anthropic`` as its provider
and ``claude-sonnet-4-6`` as its metadata name.

**The manifest fails to apply**

Check the YAML indentation, resource kind, and required fields. Reapply the
corrected manifest using ``smarter apply -f`` followed by the manifest filename.

**The API key may have been exposed**

If a real API key was committed to version control or shared unintentionally,
revoke it in the Anthropic Console and replace it with a new key.

Getting Started: Claude Code with Smarter
=========================================

Goal
----

Use Claude Code with Smarter to support AI-assisted programming by connecting
Claude Code to an Anthropic model registered in the Smarter platform.

Prerequisites
-------------

Before you begin, make sure you have:

- Access to a Smarter account and the Smarter web console.
- Claude Code installed and available in your development environment.
- Access to an Anthropic model registered and verified in Smarter.
- Basic familiarity with command-line tools and AI-assisted programming.

Setup
-----

The Anthropic provider has already been configured by the platform
administrator. Each programmer must configure their workstation to
authenticate with Smarter and route Claude Code requests through the
Smarter gateway.

Step 1: Create a Personal Smarter API Key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a personal API key in the Smarter web console:

1. Sign in to the Smarter web console.
2. Open your profile menu and select **API Keys**.
3. Select **Create API Key**, give the key a name, and copy its value.

Keep the key secure. Do not commit it to version control.

Step 2: Configure the Smarter CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Run the Smarter CLI configuration command:

.. code-block:: console

   smarter configure

Follow the prompts to configure access to your Smarter environment.
Verify that your account can connect:

.. code-block:: console

   smarter whoami

Step 3: Configure Claude Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure Claude Code to use the Smarter gateway by setting
``ANTHROPIC_BASE_URL`` to the gateway URL provided by the infrastructure
team and ``ANTHROPIC_API_KEY`` to your personal Smarter API key.

See the Step-by-Step section for configuration and verification.

Concept Overview
----------------

Claude Code is an AI coding assistant that uses a language model to help
developers understand, write, and modify code.

Anthropic provides the language model, while Smarter acts as the centralized
platform through which the organization manages access to configured models.

The Anthropic Provider registered in Smarter defines the provider endpoint
and authentication. The ``ProviderModel`` resource registers the specific
Claude model available to the programming team. Claude Code must be configured
to use the appropriate endpoint and authentication method supported by Smarter.

This setup allows developers to use AI-assisted programming while accessing
the model through the organization's Smarter platform.

Step-by-Step
------------

Step 1: Obtain the Smarter Connection Details
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before configuring Claude Code, obtain the following information from
the Smarter administrator:

- The Smarter gateway URL.
- A personal Smarter API key.
- The name of the Anthropic model configured for use through Smarter.

Do not use the Anthropic API key from the provider configuration as your
personal Smarter API key.

Step 2: Configure Claude Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure Claude Code to send requests to the Smarter gateway by setting
the following environment variables:

- ``ANTHROPIC_BASE_URL``: The gateway URL provided by the Smarter
  administrator.
- ``ANTHROPIC_API_KEY``: Your personal Smarter API key.

For example, in a Bash-compatible shell:

.. code-block:: bash

   export ANTHROPIC_BASE_URL="<smarter-gateway-url>"
   export ANTHROPIC_API_KEY="<your-smarter-api-key>"

Replace both placeholder values with the information provided by your
administrator. Do not commit credentials to version control.

Step 3: Start Claude Code
~~~~~~~~~~~~~~~~~~~~~~~~~

Open a terminal in your working directory and start Claude Code:

.. code-block:: console

   claude

Confirm that Claude Code starts successfully and can communicate with
the configured model through Smarter.

Step 4: Confirm the Request Path
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ask the Smarter administrator to confirm that your request reaches the
configured Anthropic provider through the Smarter gateway.

A successful Claude Code session alone does not prove that requests are
being routed through Smarter. Confirm the request path before using the
configuration for organizational work.

Proof of Concept
----------------

Start Claude Code in your working directory and submit a simple request,
such as asking it to explain the purpose of a file in your project.

Confirm that Claude Code returns a response.

Ask the Smarter administrator to verify that the request was processed
through the Smarter gateway and the configured Anthropic provider.

The proof of concept is successful when Claude Code returns a response
and the request path through Smarter has been confirmed.

Troubleshooting
---------------

**Claude Code cannot connect to Smarter**

Verify that ``ANTHROPIC_BASE_URL`` contains the gateway URL provided by
the Smarter administrator. Confirm that the gateway is reachable.

**Authentication fails**

Verify that ``ANTHROPIC_API_KEY`` contains a valid personal Smarter
API key. Contact the Smarter administrator if the key has expired or
is no longer valid.

**The model cannot be found**

Confirm that the model name is correct and that the Anthropic provider
is active in Smarter. Contact the administrator if the model is not
available.

**Claude Code responds, but Smarter does not show the request**

Ask the Smarter administrator to verify the request path and confirm
that Claude Code is using the configured Smarter gateway.